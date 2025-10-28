"""
ElevenLabs TTS provider.

TODO: Implement ElevenLabs API integration
- Install: pip install elevenlabs
- API docs: https://docs.elevenlabs.io/
- Features to implement:
  * Voice selection from voices.yaml
  * Rate/pitch adjustment
  * Text chunking (max 5000 chars per request)
  * Streaming or batch synthesis
  * Error handling and retries
"""
from pathlib import Path

from .base import TTSProvider
from ..shared.logger import get_logger

logger = get_logger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider (not yet implemented)."""

    def __init__(self, api_key: str, voice_id: str, **kwargs):
        """
        Initialize ElevenLabs TTS.

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use
            **kwargs: Additional parameters (model, speed, etc.)
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.kwargs = kwargs

        logger.warning("ElevenLabs TTS is not yet implemented")

    def synthesize(
        self,
        text: str,
        speaker: str,
        output_path: Path
    ) -> Path:
        """Synthesize speech (not implemented)."""
        raise NotImplementedError(
            "ElevenLabs TTS is not yet implemented. "
            "Please use 'mock' provider or implement this method. "
            "See file header for implementation guide."
        )

# TODO: Implementation outline:
# 1. Import elevenlabs library
# 2. Initialize client with API key
# 3. Chunk text if needed (max 5000 chars)
# 4. Call API with voice_id and text
# 5. Save audio to output_path
# 6. Add retry logic for network errors
# 7. Handle rate limiting
