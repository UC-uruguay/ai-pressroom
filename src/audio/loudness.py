"""
Audio loudness normalization using ffmpeg.
"""
import json
import subprocess
from pathlib import Path
from typing import Optional

from ..shared.logger import get_logger

logger = get_logger(__name__)


class LoudnessNormalizer:
    """Normalize audio loudness using ffmpeg loudnorm filter."""

    def __init__(
        self,
        target_lufs: float = -16.0,
        peak_db: float = -1.0,
        loudness_range: float = 11.0
    ):
        """
        Initialize loudness normalizer.

        Args:
            target_lufs: Target integrated loudness (LUFS)
            peak_db: Maximum true peak (dBTP)
            loudness_range: Target loudness range (LU)
        """
        self.target_lufs = target_lufs
        self.peak_db = peak_db
        self.loudness_range = loudness_range

    def normalize(
        self,
        input_path: Path,
        output_path: Path,
        two_pass: bool = True
    ) -> Path:
        """
        Normalize audio loudness.

        Args:
            input_path: Input audio file
            output_path: Output audio file
            two_pass: Use two-pass normalization for better quality

        Returns:
            Path to normalized audio file

        Raises:
            subprocess.CalledProcessError: If ffmpeg fails
        """
        logger.info(f"Normalizing loudness: {input_path.name}")

        if two_pass:
            return self._normalize_two_pass(input_path, output_path)
        else:
            return self._normalize_single_pass(input_path, output_path)

    def _normalize_single_pass(
        self,
        input_path: Path,
        output_path: Path
    ) -> Path:
        """Single-pass loudness normalization."""
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-af", (
                f"loudnorm="
                f"I={self.target_lufs}:"
                f"TP={self.peak_db}:"
                f"LRA={self.loudness_range}"
            ),
            "-ar", "44100",
            "-y",
            str(output_path)
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        logger.debug(f"Single-pass normalization complete: {output_path.name}")
        return output_path

    def _normalize_two_pass(
        self,
        input_path: Path,
        output_path: Path
    ) -> Path:
        """
        Two-pass loudness normalization for better quality.

        First pass: Measure loudness
        Second pass: Apply normalization with measured values
        """
        # First pass: Measure
        logger.debug("Running first pass (measurement)...")
        cmd1 = [
            "ffmpeg",
            "-i", str(input_path),
            "-af", (
                f"loudnorm="
                f"I={self.target_lufs}:"
                f"TP={self.peak_db}:"
                f"LRA={self.loudness_range}:"
                f"print_format=json"
            ),
            "-f", "null",
            "-"
        ]

        result = subprocess.run(cmd1, capture_output=True, text=True)

        # Parse loudness stats from stderr (ffmpeg outputs to stderr)
        stats = self._parse_loudnorm_stats(result.stderr)

        if not stats:
            logger.warning("Could not parse loudnorm stats, falling back to single-pass")
            return self._normalize_single_pass(input_path, output_path)

        # Second pass: Apply normalization
        logger.debug("Running second pass (normalization)...")
        cmd2 = [
            "ffmpeg",
            "-i", str(input_path),
            "-af", (
                f"loudnorm="
                f"I={self.target_lufs}:"
                f"TP={self.peak_db}:"
                f"LRA={self.loudness_range}:"
                f"measured_I={stats['input_i']}:"
                f"measured_TP={stats['input_tp']}:"
                f"measured_LRA={stats['input_lra']}:"
                f"measured_thresh={stats['input_thresh']}:"
                f"offset={stats['target_offset']}"
            ),
            "-ar", "44100",
            "-y",
            str(output_path)
        ]

        subprocess.run(cmd2, check=True, capture_output=True)
        logger.debug(f"Two-pass normalization complete: {output_path.name}")
        return output_path

    def _parse_loudnorm_stats(self, stderr: str) -> Optional[dict]:
        """Parse loudnorm JSON stats from ffmpeg stderr."""
        try:
            # Find JSON block in stderr
            json_start = stderr.rfind('{')
            json_end = stderr.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                return None

            json_str = stderr[json_start:json_end]
            stats = json.loads(json_str)

            return {
                'input_i': stats['input_i'],
                'input_tp': stats['input_tp'],
                'input_lra': stats['input_lra'],
                'input_thresh': stats['input_thresh'],
                'target_offset': stats['target_offset']
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse loudnorm stats: {e}")
            return None
