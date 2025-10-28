"""
Audio mixing and post-processing.
"""
from pathlib import Path
from typing import List, Optional

from pydub import AudioSegment

from .loudness import LoudnessNormalizer
from ..shared.logger import get_logger
from ..shared.settings import get_settings

logger = get_logger(__name__)


class AudioMixer:
    """Mix multiple audio files with BGM and effects."""

    def __init__(
        self,
        target_lufs: float = -16.0,
        peak_db: float = -1.0,
        bgm_volume_db: float = -15.0
    ):
        """
        Initialize audio mixer.

        Args:
            target_lufs: Target loudness in LUFS
            peak_db: Maximum peak in dB
            bgm_volume_db: BGM volume relative to main audio (in dB)
        """
        self.target_lufs = target_lufs
        self.peak_db = peak_db
        self.bgm_volume_db = bgm_volume_db
        self.normalizer = LoudnessNormalizer(target_lufs, peak_db)

    def mix_podcast(
        self,
        voice_files: List[Path],
        output_path: Path,
        bgm_path: Optional[Path] = None,
        crossfade_ms: int = 300,
        intro_silence_ms: int = 500,
        outro_silence_ms: int = 1000
    ) -> Path:
        """
        Mix voice files into a podcast episode.

        Args:
            voice_files: List of voice audio files (in order)
            output_path: Output file path
            bgm_path: Optional background music file
            crossfade_ms: Crossfade duration between voice segments
            intro_silence_ms: Silence at the beginning
            outro_silence_ms: Silence at the end

        Returns:
            Path to mixed audio file
        """
        logger.info(f"Mixing {len(voice_files)} voice segments")

        # Load and concatenate voice segments
        combined_voice = self._concatenate_voices(
            voice_files,
            crossfade_ms=crossfade_ms
        )

        # Add intro/outro silence
        intro = AudioSegment.silent(duration=intro_silence_ms)
        outro = AudioSegment.silent(duration=outro_silence_ms)
        combined_voice = intro + combined_voice + outro

        # Mix with BGM if provided
        if bgm_path and bgm_path.exists():
            logger.info(f"Adding background music: {bgm_path.name}")
            final_audio = self._mix_with_bgm(combined_voice, bgm_path)
        else:
            final_audio = combined_voice

        # Export as temporary WAV for normalization
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = output_path.with_suffix(".temp.wav")

        logger.info("Exporting mixed audio...")
        final_audio.export(
            str(temp_path),
            format="wav",
            parameters=["-ar", "44100", "-ac", "2"]
        )

        # Normalize loudness
        normalized_path = output_path.with_suffix(".normalized.wav")
        self.normalizer.normalize(temp_path, normalized_path, two_pass=True)

        # Convert to MP3
        logger.info("Converting to MP3...")
        self._convert_to_mp3(normalized_path, output_path)

        # Cleanup temporary files
        temp_path.unlink(missing_ok=True)
        normalized_path.unlink(missing_ok=True)

        logger.info(f"Mixed podcast saved: {output_path}")
        return output_path

    def _concatenate_voices(
        self,
        voice_files: List[Path],
        crossfade_ms: int = 300
    ) -> AudioSegment:
        """
        Concatenate voice files with crossfade.

        Args:
            voice_files: List of audio file paths
            crossfade_ms: Crossfade duration in milliseconds

        Returns:
            Combined AudioSegment
        """
        if not voice_files:
            raise ValueError("No voice files provided")

        # Load first file
        combined = AudioSegment.from_file(str(voice_files[0]))

        # Add remaining files with crossfade
        for voice_file in voice_files[1:]:
            segment = AudioSegment.from_file(str(voice_file))

            # Apply crossfade
            if crossfade_ms > 0 and len(combined) > crossfade_ms:
                combined = combined.append(segment, crossfade=crossfade_ms)
            else:
                combined = combined + segment

        logger.debug(f"Combined voice duration: {len(combined)/1000:.1f}s")
        return combined

    def _mix_with_bgm(
        self,
        voice: AudioSegment,
        bgm_path: Path
    ) -> AudioSegment:
        """
        Mix voice with background music.

        Args:
            voice: Voice AudioSegment
            bgm_path: Path to BGM file

        Returns:
            Mixed AudioSegment
        """
        # Load BGM
        bgm = AudioSegment.from_file(str(bgm_path))

        # Adjust BGM volume
        bgm = bgm + self.bgm_volume_db

        # Loop or trim BGM to match voice duration
        voice_duration = len(voice)

        if len(bgm) < voice_duration:
            # Loop BGM
            loops = (voice_duration // len(bgm)) + 1
            bgm = bgm * loops

        # Trim to match voice duration
        bgm = bgm[:voice_duration]

        # Fade in/out BGM
        fade_duration = min(3000, voice_duration // 10)  # 3s or 10% of duration
        bgm = bgm.fade_in(fade_duration).fade_out(fade_duration)

        # Overlay BGM under voice
        mixed = voice.overlay(bgm)

        logger.debug("BGM mixed successfully")
        return mixed

    def _convert_to_mp3(
        self,
        input_path: Path,
        output_path: Path,
        bitrate: str = "128k"
    ) -> None:
        """
        Convert audio to MP3 format.

        Args:
            input_path: Input audio file
            output_path: Output MP3 file
            bitrate: MP3 bitrate
        """
        audio = AudioSegment.from_file(str(input_path))
        audio.export(
            str(output_path),
            format="mp3",
            bitrate=bitrate,
            parameters=["-q:a", "2"]  # Quality: 2 (high quality)
        )
