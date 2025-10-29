"""
Mock TTS provider for testing.
Generates silent audio files with appropriate duration.
"""
from pathlib import Path

from pydub import AudioSegment
from pydub.generators import Sine

from .base import TTSProvider
from ..shared.logger import get_logger

logger = get_logger(__name__)


class MockTTSProvider(TTSProvider):
    """
    Mock TTS provider that generates audio for testing.

    Creates audio with:
    - Short beep tone at the start
    - Silence for the estimated duration
    - Different frequencies for different speakers (for debugging)
    """

    SPEAKER_FREQUENCIES = {
        "chatgpt": 440,   # A4
        "gemini": 523,    # C5
        "claude": 349,    # F4
        "host": 293,      # D4
    }

    def __init__(self, sample_rate: int = 24000):
        """
        Initialize mock TTS.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

    def synthesize(
        self,
        text: str,
        speaker: str,
        output_path: Path
    ) -> Path:
        """
        Generate mock audio file.

        Args:
            text: Text to synthesize (used for duration estimation)
            speaker: Speaker identifier
            output_path: Output file path

        Returns:
            Path to generated audio file
        """
        # Estimate duration: ~5 characters per second for Japanese
        estimated_duration_ms = int((len(text) / 5.0) * 1000)
        estimated_duration_ms = max(1000, estimated_duration_ms)  # Minimum 1 second

        # Get speaker frequency
        frequency = self.SPEAKER_FREQUENCIES.get(speaker, 440)

        # Generate a short beep (100ms) at speaker's frequency
        beep = Sine(frequency).to_audio_segment(duration=100, volume=-20.0)

        # Add silence for the rest of the duration
        silence = AudioSegment.silent(duration=estimated_duration_ms - 100)

        # Combine beep + silence
        audio = beep + silence

        # Set frame rate
        audio = audio.set_frame_rate(self.sample_rate)

        # Export as WAV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio.export(str(output_path), format="wav")

        logger.debug(f"Generated mock audio: {output_path.name} ({estimated_duration_ms}ms)")
        return output_path


# Factory function
def create_tts_provider(provider_type: str = "mock", **kwargs) -> TTSProvider:
    """
    Create TTS provider instance.

    Args:
        provider_type: Type of TTS provider ("mock", "elevenlabs", "gcloud")
        **kwargs: Additional arguments for provider

    Returns:
        TTSProvider instance
    """
    if provider_type == "mock":
        return MockTTSProvider(**kwargs)
    elif provider_type == "elevenlabs":
        # TODO: Implement ElevenLabs provider
        from .elevenlabs_tts import ElevenLabsTTSProvider
        return ElevenLabsTTSProvider(**kwargs)
    elif provider_type == "gcloud":
        from .gcloud_tts import GoogleCloudTTSProvider
        return GoogleCloudTTSProvider(**kwargs)
    else:
        raise ValueError(f"Unknown TTS provider: {provider_type}")
