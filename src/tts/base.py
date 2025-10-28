"""
Base TTS interface for swappable implementations.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from ..agents.debate_orchestrator import DebateLine


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        speaker: str,
        output_path: Path
    ) -> Path:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            speaker: Speaker identifier
            output_path: Output file path for audio

        Returns:
            Path to generated audio file
        """
        pass

    def synthesize_lines(
        self,
        lines: List[DebateLine],
        output_dir: Path
    ) -> List[Path]:
        """
        Synthesize multiple debate lines.

        Args:
            lines: List of DebateLine objects
            output_dir: Directory for output files

        Returns:
            List of paths to generated audio files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_files = []

        for i, line in enumerate(lines):
            output_path = output_dir / f"{i:03d}_{line.speaker}.wav"
            self.synthesize(line.text, line.speaker, output_path)
            audio_files.append(output_path)

        return audio_files
