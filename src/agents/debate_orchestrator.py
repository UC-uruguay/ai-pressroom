"""
Debate orchestrator for multi-agent discussion.

New format: 1 orchestrator + 2 debaters with confrontational dynamics.
"""
import json
import re
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Dict, Any

from openai import OpenAI
import anthropic
import google.generativeai as genai

from ..nlp.summarize import DebateTopic
from ..shared.logger import get_logger
from ..shared.retry import retry_on_api_error
from ..shared.settings import get_settings
from .debate_roles import RoleManager, RoleType, SpeakerName
from .prompt_builder import PromptBuilder

logger = get_logger(__name__)

SpeakerType = Literal["chatgpt", "gemini", "claude"]


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
    """
    Orchestrate debate with 1 orchestrator + 2 debaters.

    Roles are assigned randomly based on date:
    - Orchestrator: Facilitates and provokes confrontation
    - Debater A: Takes first position
    - Debater B: Takes opposing position
    """

    def __init__(self, date: Optional[datetime] = None):
        """
        Initialize orchestrator with API clients and role assignments.

        Args:
            date: Date for episode (used for role assignment)
        """
        self.date = date or datetime.now()
        settings = get_settings()

        # Load character configurations
        self.characters = self._load_characters(settings.config_dir)

        # Assign roles for this episode
        self.role_assignments = RoleManager.get_role_assignments(self.date)
        self.roles = {
            assignment.speaker: assignment.role
            for assignment in self.role_assignments
        }

        logger.info(f"Role assignments for {self.date.date()}:")
        for assignment in self.role_assignments:
            logger.info(
                f"  {assignment.speaker} -> {assignment.role}"
            )

        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_configured = False

        if settings.openai_api_key:
            self.openai_client = OpenAI(api_key=settings.openai_api_key)

        if settings.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key
            )

        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.gemini_configured = True

    def _load_characters(self, config_dir: Path) -> Dict[str, Any]:
        """
        Load character configurations from YAML.

        Args:
            config_dir: Configuration directory

        Returns:
            Dictionary of character configs
        """
        character_path = config_dir / "characters.yaml"

        if not character_path.exists():
            logger.warning(
                "Character configuration not found. "
                "Run 'python -m src.cli init-characters' first."
            )
            return {}

        with open(character_path, 'r', encoding='utf-8') as f:
            characters = yaml.safe_load(f) or {}

        logger.info(f"Loaded {len(characters)} character configurations")
        return characters

    def generate_script(
        self,
        topic: DebateTopic,
        target_duration_min: int = 5
    ) -> DebateScript:
        """
        Generate complete debate script with new format.

        Format:
        1. Host: Opening
        2. Each AI: Self-introduction
        3. Orchestrator: Provocative opening question
        4. Debater A: Position statement
        5. Debater B: Counter-argument
        6. Orchestrator: Deep dive question
        7. Debater A: Response
        8. Debater B: Further counter
        9. Orchestrator: Essential question
        10. Debater A: Final thoughts
        11. Debater B: Final thoughts
        12. Orchestrator: Closing provocation
        13. Host: Closing

        Args:
            topic: DebateTopic to discuss
            target_duration_min: Target duration in minutes

        Returns:
            DebateScript with all lines
        """
        logger.info(f"Generating debate script for: {topic.title}")

        lines = []

        # Phase 1: Opening
        lines.append(self._create_opening(topic))

        # Phase 2: Self-introductions
        intro_lines = self._generate_introductions()
        lines.extend(intro_lines)

        # Phase 3: Debate (orchestrator-led)
        debate_lines = self._generate_debate_exchange(topic)
        lines.extend(debate_lines)

        # Phase 4: Closing
        lines.append(self._create_closing())

        # Calculate total duration
        total_duration = sum(
            line.estimated_duration_sec + line.pause_after_sec
            for line in lines
        )

        script = DebateScript(
            title=topic.title,
            topic_summary=topic.summary,
            lines=lines,
            total_duration_sec=total_duration
        )

        logger.info(
            f"Generated script with {len(lines)} lines, "
            f"~{total_duration:.1f} seconds"
        )

        return script

    def _create_opening(self, topic: DebateTopic) -> DebateLine:
        """Create opening line from orchestrator."""
        # Get orchestrator
        orchestrator = self._get_speaker_by_role("orchestrator")
        character = self.characters.get(orchestrator, {})

        # Build opening prompt
        role = self.roles.get(orchestrator)
        system_prompt = PromptBuilder.build_system_prompt(
            orchestrator, role, character, topic.title
        )

        user_prompt = f"""討論を開始してください。

トピック: 「{topic.title}」
背景: {topic.summary}

**1文で**簡潔に、トピックを紹介し討論を始めてください。
例: 「今日のトピックは「{topic.title}」です。{topic.summary} 本日は○○○○の3名にお集まりいただきました。」

20-30文字程度で簡潔に。"""

        try:
            text = self._call_llm(
                orchestrator,
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.7
            ).strip()
            text = self._clean_markdown(text)
        except Exception as e:
            logger.error(f"Failed to generate opening: {e}")
            text = f"今日のトピックは「{topic.title}」です。{topic.summary}"

        return DebateLine(
            speaker=orchestrator,
            text=text,
            estimated_duration_sec=len(text) * 0.15,
            pause_after_sec=1.0
        )

    def _generate_introductions(self) -> List[DebateLine]:
        """
        Generate self-introductions for all AIs.

        Returns:
            List of introduction lines
        """
        logger.info("Generating self-introductions...")

        lines = []

        for assignment in self.role_assignments:
            speaker = assignment.speaker
            role = assignment.role
            character = self.characters.get(speaker, {})

            if not character:
                logger.warning(
                    f"No character config for {speaker}, skipping intro"
                )
                continue

            # Generate introduction
            intro_text = self._generate_introduction(
                speaker, character, role
            )

            lines.append(DebateLine(
                speaker=speaker,
                text=intro_text,
                estimated_duration_sec=len(intro_text) * 0.15,
                pause_after_sec=0.8
            ))

        return lines

    def _generate_introduction(
        self,
        speaker: SpeakerName,
        character: Dict[str, Any],
        role: RoleType
    ) -> str:
        """
        Generate self-introduction for one AI.

        Args:
            speaker: Speaker name
            character: Character configuration
            role: Assigned role

        Returns:
            Introduction text
        """
        prompt = PromptBuilder.build_introduction_prompt(
            speaker, character, role
        )

        try:
            response = self._call_llm(speaker, prompt, temperature=0.8)
            cleaned_response = self._clean_markdown(response.strip())
            return cleaned_response
        except Exception as e:
            logger.error(f"Failed to generate intro for {speaker}: {e}")
            # Fallback
            ai_name = character.get("ai_name", speaker.title())
            company = character.get("company", "")
            persona = character.get("persona_name", ai_name)
            return f"{company}を代表して参加しております、{ai_name}の{persona}です。"

    def _generate_debate_exchange(
        self,
        topic: DebateTopic
    ) -> List[DebateLine]:
        """
        Generate debate exchange between orchestrator and debaters.

        Flow:
        1. Orchestrator: Provocative question
        2. Debater A: Position
        3. Debater B: Counter-position
        4. Orchestrator: Deep dive
        5. Debater A: Response
        6. Debater B: Further counter
        7. Orchestrator: Essential question
        8. Debater A: Final thought
        9. Debater B: Final thought
        10. Orchestrator: Closing provocation

        Args:
            topic: Debate topic

        Returns:
            List of debate lines
        """
        logger.info("Generating debate exchange...")

        lines = []

        # Get role assignments
        orchestrator = self._get_speaker_by_role("orchestrator")
        debater_a = self._get_speaker_by_role("debater_a")
        debater_b = self._get_speaker_by_role("debater_b")

        # Build system prompts
        system_prompts = {}
        for speaker in [orchestrator, debater_a, debater_b]:
            character = self.characters.get(speaker, {})
            role = self.roles.get(speaker)
            system_prompts[speaker] = PromptBuilder.build_system_prompt(
                speaker, role, character, topic.title
            )

        # Conversation history for context
        conversation = []

        # Turn 1: Orchestrator opens with provocative question
        orchestrator_q1 = self._generate_turn(
            speaker=orchestrator,
            system_prompt=system_prompts[orchestrator],
            user_prompt=(
                f"トピック「{topic.title}」について、討論を開始してください。\n"
                f"背景: {topic.summary}\n\n"
                "討論者たちに**対立する立場**を取らせるような、"
                "**挑発的で本質を突く質問**をしてください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(orchestrator, orchestrator_q1))
        conversation.append({"speaker": orchestrator, "text": orchestrator_q1})

        # Turn 2: Debater A responds
        debater_a_r1 = self._generate_turn(
            speaker=debater_a,
            system_prompt=system_prompts[debater_a],
            user_prompt=(
                f"トピック「{topic.title}」について討論しています。\n\n"
                f"オーケストレーターの質問: 「{orchestrator_q1}」\n\n"
                "このトピックに関して、あなたの立場を明確に表明してください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(debater_a, debater_a_r1))
        conversation.append({"speaker": debater_a, "text": debater_a_r1})

        # Turn 3: Debater B counters
        debater_b_r1 = self._generate_turn(
            speaker=debater_b,
            system_prompt=system_prompts[debater_b],
            user_prompt=(
                f"トピック「{topic.title}」について討論しています。\n\n"
                f"討論者Aの意見: 「{debater_a_r1}」\n\n"
                "このトピックに関して、**異なる視点**から反論してください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(debater_b, debater_b_r1))
        conversation.append({"speaker": debater_b, "text": debater_b_r1})

        # Turn 4: Orchestrator digs deeper
        orchestrator_q2 = self._generate_turn(
            speaker=orchestrator,
            system_prompt=system_prompts[orchestrator],
            user_prompt=(
                f"トピック「{topic.title}」について、両者の意見を聞きました。\n\n"
                "このトピックに焦点を当てたまま、さらに**本質を突く質問**をして、議論を深めてください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(orchestrator, orchestrator_q2))
        conversation.append({"speaker": orchestrator, "text": orchestrator_q2})

        # Turn 5: Debater A responds to deeper question
        debater_a_r2 = self._generate_turn(
            speaker=debater_a,
            system_prompt=system_prompts[debater_a],
            user_prompt=(
                f"トピック「{topic.title}」に関するオーケストレーターの質問: 「{orchestrator_q2}」\n\n"
                "このトピックの範囲内で、この質問に応答しつつ、あなたの立場を強化してください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(debater_a, debater_a_r2))
        conversation.append({"speaker": debater_a, "text": debater_a_r2})

        # Turn 6: Debater B counters again
        debater_b_r2 = self._generate_turn(
            speaker=debater_b,
            system_prompt=system_prompts[debater_b],
            user_prompt=(
                f"トピック「{topic.title}」に関する討論者Aの応答: 「{debater_a_r2}」\n\n"
                "このトピックの範囲内で、さらに**批判的な視点**から反論してください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(debater_b, debater_b_r2))
        conversation.append({"speaker": debater_b, "text": debater_b_r2})

        # Turn 7: Orchestrator asks essential question
        orchestrator_q3 = self._generate_turn(
            speaker=orchestrator,
            system_prompt=system_prompts[orchestrator],
            user_prompt=(
                f"トピック「{topic.title}」についての議論が深まってきました。\n\n"
                "最後に、**このトピックの本質は何か**を問う質問をしてください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(orchestrator, orchestrator_q3))
        conversation.append({"speaker": orchestrator, "text": orchestrator_q3})

        # Turn 8: Debater A final thought
        debater_a_r3 = self._generate_turn(
            speaker=debater_a,
            system_prompt=system_prompts[debater_a],
            user_prompt=(
                f"トピック「{topic.title}」に関する最後の質問: 「{orchestrator_q3}」\n\n"
                "このトピックについて、あなたの**最終的な見解**を述べてください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(debater_a, debater_a_r3))
        conversation.append({"speaker": debater_a, "text": debater_a_r3})

        # Turn 9: Debater B final thought
        debater_b_r3 = self._generate_turn(
            speaker=debater_b,
            system_prompt=system_prompts[debater_b],
            user_prompt=(
                f"トピック「{topic.title}」に関する最後の質問: 「{orchestrator_q3}」\n\n"
                "このトピックについて、あなたの**最終的な見解**を述べてください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(debater_b, debater_b_r3))
        conversation.append({"speaker": debater_b, "text": debater_b_r3})

        # Turn 10: Orchestrator closing provocation
        orchestrator_closing = self._generate_turn(
            speaker=orchestrator,
            system_prompt=system_prompts[orchestrator],
            user_prompt=(
                f"トピック「{topic.title}」についての討論を締めくくってください。\n\n"
                "安易な結論ではなく、**このトピックについてさらなる思考を促す挑発的な一言**で終わらせてください。"
            ),
            conversation=conversation
        )
        lines.append(self._create_line(orchestrator, orchestrator_closing))

        return lines

    def _generate_turn(
        self,
        speaker: SpeakerName,
        system_prompt: str,
        user_prompt: str,
        conversation: List[Dict[str, str]]
    ) -> str:
        """
        Generate one turn of dialogue.

        Args:
            speaker: Speaker generating the turn
            system_prompt: System prompt for this speaker
            user_prompt: User prompt for this turn
            conversation: Conversation history

        Returns:
            Generated text
        """
        # Build context from conversation
        context = "\n\n".join([
            f"{turn['speaker']}: {turn['text']}"
            for turn in conversation[-3:]  # Last 3 turns for context
        ])

        if context:
            full_prompt = f"## これまでの議論\n\n{context}\n\n---\n\n{user_prompt}"
        else:
            full_prompt = user_prompt

        try:
            response = self._call_llm(
                speaker,
                full_prompt,
                system_prompt=system_prompt,
                temperature=0.85
            )
            # Remove markdown symbols for TTS
            cleaned_response = self._clean_markdown(response.strip())
            return cleaned_response
        except Exception as e:
            logger.error(f"Failed to generate turn for {speaker}: {e}")
            return "（発言を生成できませんでした）"

    def _create_line(self, speaker: SpeakerName, text: str) -> DebateLine:
        """Create DebateLine from speaker and text."""
        return DebateLine(
            speaker=speaker,
            text=text,
            estimated_duration_sec=len(text) * 0.15,
            pause_after_sec=0.8
        )

    def _create_closing(self) -> DebateLine:
        """Create closing line from orchestrator."""
        # Get orchestrator
        orchestrator = self._get_speaker_by_role("orchestrator")
        character = self.characters.get(orchestrator, {})

        # Build closing prompt
        role = self.roles.get(orchestrator)
        system_prompt = PromptBuilder.build_system_prompt(
            orchestrator, role, character, ""
        )

        user_prompt = """討論を締めくくってください。

**1文で**簡潔に、お聞きいただきありがとうございましたという感謝の言葉で終えてください。
例: 「本日の討論は以上です。お聞きいただきありがとうございました。」

15文字程度で簡潔に。"""

        try:
            text = self._call_llm(
                orchestrator,
                user_prompt,
                system_prompt=system_prompt,
                temperature=0.7
            ).strip()
            text = self._clean_markdown(text)
        except Exception as e:
            logger.error(f"Failed to generate closing: {e}")
            text = "本日の討論は以上です。お聞きいただきありがとうございました。"

        return DebateLine(
            speaker=orchestrator,
            text=text,
            estimated_duration_sec=len(text) * 0.15,
            pause_after_sec=0.5
        )

    def _get_speaker_by_role(self, role: RoleType) -> SpeakerName:
        """Get speaker assigned to role."""
        for speaker, assigned_role in self.roles.items():
            if assigned_role == role:
                return speaker
        raise ValueError(f"No speaker assigned to role: {role}")

    def _call_llm(
        self,
        speaker: SpeakerName,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Call appropriate LLM for speaker.

        Args:
            speaker: Speaker name
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Temperature for generation

        Returns:
            Generated text
        """
        if speaker == "chatgpt":
            return self._call_openai(prompt, system_prompt, temperature)
        elif speaker == "gemini":
            return self._call_gemini(prompt, system_prompt, temperature)
        elif speaker == "claude":
            return self._call_anthropic(prompt, system_prompt, temperature)
        else:
            raise ValueError(f"Unknown speaker: {speaker}")

    @retry_on_api_error(max_attempts=3, min_wait=2)
    def _call_openai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Call OpenAI API."""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not available")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=300
        )

        return response.choices[0].message.content

    @retry_on_api_error(max_attempts=3, min_wait=2)
    def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Call Gemini API."""
        if not self.gemini_configured:
            raise RuntimeError("Gemini not configured")

        # Combine system and user prompts
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"

        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=300
            )
        )

        return response.text

    @retry_on_api_error(max_attempts=3, min_wait=2)
    def _call_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Call Anthropic API."""
        if not self.anthropic_client:
            raise RuntimeError("Anthropic client not available")

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            system=system_prompt or "",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )

        return response.content[0].text

    def _clean_markdown(self, text: str) -> str:
        """
        Remove markdown symbols from text for TTS.

        Args:
            text: Text with potential markdown symbols

        Returns:
            Cleaned text
        """
        # Remove bold/italic markers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'__(.+?)__', r'\1', text)      # __bold__
        text = re.sub(r'\*(.+?)\*', r'\1', text)      # *italic*
        text = re.sub(r'_(.+?)_', r'\1', text)        # _italic_

        # Remove headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`(.+?)`', r'\1', text)

        # Remove lists markers
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

        # Remove links
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

        return text
