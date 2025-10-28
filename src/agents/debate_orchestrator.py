"""
Debate orchestrator for multi-agent discussion.
Generates debate scripts with multiple AI personalities.
"""
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Literal, Optional

from openai import OpenAI
import anthropic
# Note: google-generativeai would be imported here for Gemini support

from ..nlp.summarize import DebateTopic
from ..shared.logger import get_logger
from ..shared.retry import retry_on_api_error
from ..shared.settings import get_settings

logger = get_logger(__name__)

SpeakerType = Literal["chatgpt", "gemini", "claude", "host"]


@dataclass
class DebateLine:
    """Single line in debate script."""
    speaker: SpeakerType
    text: str
    estimated_duration_sec: float
    pause_after_sec: float = 0.5


@dataclass
class DebateScript:
    """Complete debate script."""
    title: str
    topic_summary: str
    lines: List[DebateLine]
    total_duration_sec: float

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "DebateScript":
        """Load from JSON string."""
        data = json.loads(json_str)
        data["lines"] = [DebateLine(**line) for line in data["lines"]]
        return cls(**data)


class DebateOrchestrator:
    """Orchestrate debate between AI agents."""

    def __init__(self):
        """Initialize orchestrator with API clients."""
        settings = get_settings()

        # Load system prompts
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.system_prompts = self._load_system_prompts()

        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None

        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)

        if settings.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        # TODO: Initialize Gemini client when google-generativeai is configured

    def _load_system_prompts(self) -> dict[str, str]:
        """Load system prompts from files."""
        prompts = {}
        for speaker in ["chatgpt", "gemini", "claude"]:
            prompt_file = self.prompts_dir / f"system_{speaker}.txt"
            if prompt_file.exists():
                prompts[speaker] = prompt_file.read_text(encoding="utf-8")
            else:
                logger.warning(f"System prompt not found: {prompt_file}")
                prompts[speaker] = f"あなたは{speaker}として討論に参加しています。"
        return prompts

    def generate_script(self, topic: DebateTopic, target_duration_min: int = 5) -> DebateScript:
        """
        Generate complete debate script.

        Args:
            topic: DebateTopic to discuss
            target_duration_min: Target duration in minutes

        Returns:
            DebateScript with all lines
        """
        logger.info(f"Generating debate script for: {topic.title}")

        # Create debate structure: Opening -> Discussion -> Conclusion
        lines = []

        # 1. Opening by host
        lines.append(DebateLine(
            speaker="host",
            text=f"今日のトピックは「{topic.title}」です。{topic.summary}",
            estimated_duration_sec=10.0,
            pause_after_sec=1.0
        ))

        # 2. Generate main discussion (3-4 rounds)
        discussion_lines = self._generate_discussion(topic, rounds=3)
        lines.extend(discussion_lines)

        # 3. Conclusion
        conclusion_lines = self._generate_conclusion(topic)
        lines.extend(conclusion_lines)

        # 4. Closing by host
        lines.append(DebateLine(
            speaker="host",
            text="本日の討論は以上です。お聞きいただきありがとうございました。",
            estimated_duration_sec=5.0,
            pause_after_sec=0.5
        ))

        total_duration = sum(line.estimated_duration_sec + line.pause_after_sec for line in lines)

        script = DebateScript(
            title=topic.title,
            topic_summary=topic.summary,
            lines=lines,
            total_duration_sec=total_duration
        )

        logger.info(f"Generated script with {len(lines)} lines, ~{total_duration:.1f} seconds")
        return script

    def _generate_discussion(self, topic: DebateTopic, rounds: int = 3) -> List[DebateLine]:
        """
        Generate discussion rounds.

        Args:
            topic: DebateTopic
            rounds: Number of discussion rounds

        Returns:
            List of DebateLine objects
        """
        lines = []
        speakers = ["chatgpt", "gemini", "claude"]

        for round_num in range(rounds):
            # Each round: all speakers contribute
            for speaker in speakers:
                text = self._generate_utterance(
                    speaker=speaker,
                    topic=topic,
                    round_num=round_num,
                    previous_lines=lines
                )

                # Estimate duration (rough: 5 chars per second for Japanese)
                duration = len(text) / 5.0

                lines.append(DebateLine(
                    speaker=speaker,
                    text=text,
                    estimated_duration_sec=duration,
                    pause_after_sec=0.8
                ))

        return lines

    @retry_on_api_error(max_attempts=2)
    def _generate_utterance(
        self,
        speaker: SpeakerType,
        topic: DebateTopic,
        round_num: int,
        previous_lines: List[DebateLine]
    ) -> str:
        """
        Generate a single utterance for a speaker.

        Args:
            speaker: Speaker name
            topic: DebateTopic
            round_num: Current round number
            previous_lines: Previous debate lines for context

        Returns:
            Generated text
        """
        # Build context from previous lines
        context = "\n".join([
            f"{line.speaker}: {line.text}"
            for line in previous_lines[-6:]  # Last 6 lines for context
        ])

        # Create prompt based on round
        if round_num == 0:
            instruction = "このトピックについて、あなたの最初の意見を述べてください。"
        elif round_num == 1:
            instruction = "他の参加者の意見を踏まえて、あなたの見解を深めてください。"
        else:
            instruction = "議論を総括し、重要なポイントを強調してください。"

        user_prompt = f"""トピック: {topic.title}
概要: {topic.summary}
論点:
{chr(10).join(f"- {point}" for point in topic.key_points)}

これまでの議論:
{context if context else "(まだ発言はありません)"}

{instruction}
2-3文程度で簡潔に述べてください。"""

        # Use appropriate LLM based on speaker
        if speaker == "chatgpt" and self.openai_client:
            return self._call_openai(user_prompt, self.system_prompts["chatgpt"])
        elif speaker == "claude" and self.anthropic_client:
            return self._call_anthropic(user_prompt, self.system_prompts["claude"])
        elif speaker == "gemini":
            # TODO: Implement Gemini API call
            return self._fallback_response(speaker, topic, round_num)
        else:
            return self._fallback_response(speaker, topic, round_num)

    def _call_openai(self, user_prompt: str, system_prompt: str) -> str:
        """Call OpenAI API."""
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(self, user_prompt: str, system_prompt: str) -> str:
        """Call Anthropic API."""
        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.content[0].text.strip()

    def _fallback_response(self, speaker: str, topic: DebateTopic, round_num: int) -> str:
        """Generate fallback response when API is not available."""
        responses = {
            0: f"「{topic.title}」について、興味深いトピックですね。",
            1: f"この問題には様々な側面があると思います。",
            2: f"総合的に見て、バランスの取れた対応が必要ですね。"
        }
        return responses.get(round_num, "なるほど、重要な視点ですね。")

    def _generate_conclusion(self, topic: DebateTopic) -> List[DebateLine]:
        """Generate conclusion section."""
        return [
            DebateLine(
                speaker="host",
                text="それでは、本日の討論をまとめましょう。",
                estimated_duration_sec=4.0,
                pause_after_sec=0.5
            ),
            DebateLine(
                speaker="chatgpt",
                text="活発な議論ができました。様々な視点から考えることができて良かったです。",
                estimated_duration_sec=8.0,
                pause_after_sec=0.5
            )
        ]
