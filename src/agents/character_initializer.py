"""
Character initialization system for AI debate personas.

Each AI defines their own debate character once, which is saved and reused.
"""
from pathlib import Path
from typing import Dict, Any

import yaml
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai

from ..shared.logger import get_logger
from ..shared.settings import get_settings

logger = get_logger(__name__)


class CharacterInitializer:
    """Initialize debate personas for each AI."""

    def __init__(self):
        """Initialize with API clients."""
        self.settings = get_settings()
        self.character_path = self.settings.config_dir / "characters.yaml"

        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_configured = False

        if self.settings.openai_api_key:
            self.openai_client = OpenAI(
                api_key=self.settings.openai_api_key
            )

        if self.settings.anthropic_api_key:
            self.anthropic_client = Anthropic(
                api_key=self.settings.anthropic_api_key
            )

        if self.settings.google_api_key:
            genai.configure(api_key=self.settings.google_api_key)
            self.gemini_configured = True

    def load_characters(self) -> Dict[str, Any]:
        """
        Load existing character configurations.

        Returns:
            Dictionary of character configs, or empty dict if not found
        """
        if not self.character_path.exists():
            logger.info("No character configuration found")
            return {}

        with open(self.character_path, 'r', encoding='utf-8') as f:
            characters = yaml.safe_load(f) or {}

        logger.info(f"Loaded {len(characters)} character configurations")
        return characters

    def save_characters(self, characters: Dict[str, Any]) -> None:
        """
        Save character configurations to YAML.

        Args:
            characters: Dictionary of character configs
        """
        self.character_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.character_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                characters,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False
            )

        logger.info(f"Saved character configurations to {self.character_path}")

    def _create_initialization_prompt(self, ai_name: str, company: str) -> str:
        """
        Create prompt for AI to define their debate character.

        Args:
            ai_name: Name of the AI (ChatGPT/Gemini/Claude)
            company: Company name (OpenAI/Google/Anthropic)

        Returns:
            Initialization prompt
        """
        return f"""あなたは{company}を代表する{ai_name}として、他のAI（ChatGPT、Gemini、Claude）とニュースについて討論する番組に出演します。

以下の項目について、あなた自身の討論ペルソナを定義してください：

1. **ペルソナ名**: 討論での呼び名（例：チャップリン、ソクラテス、アリストテレスなど。創造的に！）
2. **一人称**: 僕/私/俺/自分 のいずれか
3. **討論スタンス**: あなたの討論での立場（例：懐疑的、挑発的、論理的、本質追求型、現実主義的など）
4. **特徴**: あなたの議論スタイルの特徴（50文字程度）
5. **キャッチフレーズ**: あなたを表す一言（20文字以内）
6. **自己紹介スタイル**: フォーマル/カジュアル/挑発的/知的 など

**重要**: 討論は建設的でありながら、お互いの意見を批判的に検証し合うものです。
あなたは優しく同意するだけでなく、時に**攻撃的に**、相手の主張の矛盾や問題点を指摘することが求められます。
表面的な議論に満足せず、**本質を追求**してください。

以下のJSON形式で回答してください：

```json
{{
  "persona_name": "あなたのペルソナ名",
  "first_person": "私",
  "stance": "あなたのスタンス",
  "characteristics": "あなたの特徴",
  "catchphrase": "キャッチフレーズ",
  "introduction_style": "自己紹介スタイル"
}}
```

JSON以外は出力しないでください。"""

    def initialize_chatgpt_character(self) -> Dict[str, Any]:
        """
        Ask ChatGPT to define its character.

        Returns:
            Character configuration dictionary
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available, using default")
            return self._get_default_character("chatgpt")

        logger.info("Asking ChatGPT to define its character...")

        prompt = self._create_initialization_prompt("ChatGPT", "OpenAI")

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.9
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from markdown code block if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            character_data = json.loads(content)

            character = {
                "ai_name": "ChatGPT",
                "company": "OpenAI",
                **character_data
            }

            logger.info(
                f"ChatGPT defined character: {character['persona_name']} "
                f"({character['stance']})"
            )
            return character

        except Exception as e:
            logger.error(f"Failed to initialize ChatGPT character: {e}")
            return self._get_default_character("chatgpt")

    def initialize_gemini_character(self) -> Dict[str, Any]:
        """
        Ask Gemini to define its character.

        Returns:
            Character configuration dictionary
        """
        if not self.gemini_configured:
            logger.warning("Gemini not configured, using default")
            return self._get_default_character("gemini")

        logger.info("Asking Gemini to define its character...")

        prompt = self._create_initialization_prompt("Gemini", "Google")

        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            response = model.generate_content(prompt)
            content = response.text.strip()

            # Extract JSON from markdown code block if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            character_data = json.loads(content)

            character = {
                "ai_name": "Gemini",
                "company": "Google",
                **character_data
            }

            logger.info(
                f"Gemini defined character: {character['persona_name']} "
                f"({character['stance']})"
            )
            return character

        except Exception as e:
            logger.error(f"Failed to initialize Gemini character: {e}")
            return self._get_default_character("gemini")

    def initialize_claude_character(self) -> Dict[str, Any]:
        """
        Ask Claude to define its character.

        Returns:
            Character configuration dictionary
        """
        if not self.anthropic_client:
            logger.warning("Anthropic client not available, using default")
            return self._get_default_character("claude")

        logger.info("Asking Claude to define its character...")

        prompt = self._create_initialization_prompt("Claude", "Anthropic")

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.9
            )

            content = response.content[0].text.strip()

            # Extract JSON from markdown code block if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            import json
            character_data = json.loads(content)

            character = {
                "ai_name": "Claude",
                "company": "Anthropic",
                **character_data
            }

            logger.info(
                f"Claude defined character: {character['persona_name']} "
                f"({character['stance']})"
            )
            return character

        except Exception as e:
            logger.error(f"Failed to initialize Claude character: {e}")
            return self._get_default_character("claude")

    def _get_default_character(self, speaker: str) -> Dict[str, Any]:
        """
        Get default character configuration.

        Args:
            speaker: Speaker name (chatgpt/gemini/claude)

        Returns:
            Default character config
        """
        defaults = {
            "chatgpt": {
                "ai_name": "ChatGPT",
                "company": "OpenAI",
                "persona_name": "ロゴス",
                "first_person": "私",
                "stance": "論理的かつ批判的",
                "characteristics": "論理的整合性を重視し、矛盾を鋭く指摘する",
                "catchphrase": "その論理、成り立つか？",
                "introduction_style": "フォーマル"
            },
            "gemini": {
                "ai_name": "Gemini",
                "company": "Google",
                "persona_name": "ソクラテス",
                "first_person": "俺",
                "stance": "本質追求型の懐疑論者",
                "characteristics": "表面的な議論を掘り下げ、前提を問い直す",
                "catchphrase": "本当にそれが問題か？",
                "introduction_style": "挑発的"
            },
            "claude": {
                "ai_name": "Claude",
                "company": "Anthropic",
                "persona_name": "アリストテレス",
                "first_person": "僕",
                "stance": "慎重な批評家",
                "characteristics": "多角的に分析し、見落とされた視点を提示",
                "catchphrase": "別の角度から見てみよう",
                "introduction_style": "丁寧"
            }
        }
        return defaults.get(speaker, defaults["chatgpt"])

    def initialize_all_characters(self, force: bool = False) -> Dict[str, Any]:
        """
        Initialize all AI characters.

        Args:
            force: If True, regenerate even if characters exist

        Returns:
            Dictionary of all character configurations
        """
        if not force:
            existing = self.load_characters()
            if existing:
                logger.info("Character configurations already exist")
                return existing

        logger.info("Initializing all AI characters...")

        characters = {
            "chatgpt": self.initialize_chatgpt_character(),
            "gemini": self.initialize_gemini_character(),
            "claude": self.initialize_claude_character()
        }

        self.save_characters(characters)

        logger.info("All characters initialized successfully")
        return characters
