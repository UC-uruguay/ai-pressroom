"""
Google Cloud Text-to-Speech provider.

API docs: https://cloud.google.com/text-to-speech/docs
"""
import re
from pathlib import Path
from typing import Optional, Dict

from google.cloud import texttospeech
from google.api_core import exceptions as google_exceptions

from .base import TTSProvider
from ..shared.logger import get_logger
from ..shared.retry import retry_on_api_error

logger = get_logger(__name__)

# Common kanji reading corrections
# Format: {kanji_pattern: (reading, context_hint)}
READING_CORRECTIONS: Dict[str, str] = {
    # Common misreadings
    "本質": "ホンシツ",
    "根本": "コンポン",  # Default to コンポン, but context-dependent
    "真理": "シンリ",
    "探求": "タンキュウ",
    "探究": "タンキュウ",
    "深層": "シンソウ",
}


class GoogleCloudTTSProvider(TTSProvider):
    """
    Google Cloud Text-to-Speech provider.

    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable
    pointing to a service account JSON file.
    """

    def __init__(
        self,
        voice_name: str = "ja-JP-Neural2-C",
        language_code: str = "ja-JP",
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        **kwargs
    ):
        """
        Initialize Google Cloud TTS client.

        Args:
            voice_name: Voice name (e.g., "ja-JP-Neural2-C")
            language_code: Language code (e.g., "ja-JP")
            speaking_rate: Speech speed (0.25 to 4.0, default 1.0)
            pitch: Voice pitch (-20.0 to 20.0, default 0.0)
            **kwargs: Additional parameters

        Raises:
            Exception: If GOOGLE_APPLICATION_CREDENTIALS is not set
        """
        self.voice_name = voice_name
        self.language_code = language_code
        self.speaking_rate = speaking_rate
        self.pitch = pitch
        self.kwargs = kwargs

        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info(
                f"Initialized Google Cloud TTS: {voice_name} "
                f"(rate={speaking_rate}, pitch={pitch})"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Google Cloud TTS client: {e}"
            )
            logger.error(
                "Make sure GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable is set"
            )
            raise

    def _text_to_ssml(self, text: str) -> str:
        """
        Convert text to SSML with reading corrections.

        Args:
            text: Plain text

        Returns:
            SSML markup
        """
        # Escape special XML characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')

        # Apply reading corrections
        for kanji, reading in READING_CORRECTIONS.items():
            # Use <sub> tag to specify pronunciation
            pattern = re.escape(kanji)
            replacement = f'<sub alias="{reading}">{kanji}</sub>'
            text = re.sub(pattern, replacement, text)

        # Wrap in SSML speak tag
        ssml = f'<speak>{text}</speak>'

        return ssml

    @retry_on_api_error(max_attempts=3, min_wait=1)
    def synthesize(
        self,
        text: str,
        speaker: str,
        output_path: Path
    ) -> Path:
        """
        Synthesize speech from text using Google Cloud TTS.

        Args:
            text: Text to synthesize
            speaker: Speaker name (for logging only)
            output_path: Path where audio file will be saved

        Returns:
            Path to the generated audio file (WAV format)

        Raises:
            google_exceptions.GoogleAPIError: If API call fails
            IOError: If file write fails
        """
        logger.debug(
            f"Synthesizing speech for {speaker}: "
            f"{text[:50]}... ({len(text)} chars)"
        )

        try:
            # Convert text to SSML with reading corrections
            ssml = self._text_to_ssml(text)
            logger.debug(f"SSML: {ssml[:100]}...")

            # Build synthesis input with SSML
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

            # Configure voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name
            )

            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000,
                speaking_rate=self.speaking_rate,
                pitch=self.pitch
            )

            # Call the API
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Write audio content to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.audio_content)

            logger.debug(f"Saved audio: {output_path}")
            return output_path

        except google_exceptions.GoogleAPIError as e:
            logger.error(
                f"Google Cloud TTS API error for {speaker}: {e}"
            )
            raise
        except IOError as e:
            logger.error(f"Failed to write audio file {output_path}: {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during synthesis for {speaker}: {e}"
            )
            raise
