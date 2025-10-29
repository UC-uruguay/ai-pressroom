"""
Generate video from debate script and audio.

Creates video with speaker-switching avatars synchronized to audio.
"""
import subprocess
from pathlib import Path
from typing import Dict, Optional

from ..agents.debate_orchestrator import DebateScript
from ..shared.logger import get_logger
from .avatar_generator import AvatarGenerator

logger = get_logger(__name__)


class VideoGenerator:
    """Generate video with speaker transitions."""

    def __init__(
        self,
        work_dir: Path,
        characters: Dict[str, Dict]
    ):
        """
        Initialize video generator.

        Args:
            work_dir: Working directory for video generation
            characters: Character configurations
        """
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.characters = characters

        # Create avatar generator
        avatar_dir = work_dir / "avatars"
        self.avatar_gen = AvatarGenerator(avatar_dir)

    def generate_video(
        self,
        script: DebateScript,
        audio_path: Path,
        output_path: Path
    ) -> Path:
        """
        Generate video from debate script and audio.

        Args:
            script: Debate script with timing information
            audio_path: Path to final mixed audio (MP3)
            output_path: Path to save output video

        Returns:
            Path to generated video
        """
        logger.info("Generating video from debate script...")

        # Step 1: Generate avatar images
        logger.info("Generating avatar images...")
        avatars = self.avatar_gen.generate_all_avatars(self.characters)

        # Step 2: Create video segments for each speaker
        logger.info("Creating video segments...")
        segment_list = self._create_segment_list(script, avatars)

        # Step 3: Generate concat file for FFmpeg
        concat_file = self._create_concat_file(segment_list)

        # Step 4: Use FFmpeg to create video with speaker transitions
        logger.info("Rendering video with FFmpeg...")
        self._render_video(concat_file, audio_path, output_path)

        logger.info(f"Video generated successfully: {output_path}")
        return output_path

    def _create_segment_list(
        self,
        script: DebateScript,
        avatars: Dict[str, Path]
    ) -> list[dict]:
        """
        Create list of video segments with timing.

        Args:
            script: Debate script
            avatars: Dictionary of avatar image paths

        Returns:
            List of segment info dicts
        """
        segments = []
        current_time = 0.0

        for line in script.lines:
            speaker = line.speaker
            duration = line.estimated_duration_sec + line.pause_after_sec

            # Get avatar path (fallback to chatgpt if not found)
            avatar_path = avatars.get(
                speaker,
                avatars.get("chatgpt", list(avatars.values())[0])
            )

            segments.append({
                "speaker": speaker,
                "avatar": avatar_path,
                "start": current_time,
                "duration": duration,
                "text": line.text
            })

            current_time += duration

        return segments

    def _create_concat_file(self, segments: list[dict]) -> Path:
        """
        Create FFmpeg concat demuxer file.

        Args:
            segments: List of segment info

        Returns:
            Path to concat file
        """
        concat_path = self.work_dir / "concat_list.txt"

        # First, create individual segment videos with speaker name overlay
        segment_videos = []

        for i, seg in enumerate(segments):
            seg_video = self.work_dir / f"segment_{i:04d}.mp4"
            segment_videos.append(seg_video)

            # Skip if already exists
            if seg_video.exists():
                continue

            # Create video segment with text overlay
            self._create_segment_video(
                avatar_path=seg["avatar"],
                duration=seg["duration"],
                speaker_name=seg["speaker"].upper(),
                output_path=seg_video
            )

        # Create concat file
        with open(concat_path, 'w', encoding='utf-8') as f:
            for seg_video in segment_videos:
                f.write(f"file '{seg_video.absolute()}'\n")

        logger.info(f"Created concat file with {len(segment_videos)} segments")
        return concat_path

    def _create_segment_video(
        self,
        avatar_path: Path,
        duration: float,
        speaker_name: str,
        output_path: Path
    ) -> None:
        """
        Create a single video segment with speaker name overlay.

        Args:
            avatar_path: Path to avatar image
            duration: Duration in seconds
            speaker_name: Speaker name to display
            output_path: Output video path
        """
        # FFmpeg command to create video from image with text overlay
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-loop", "1",
            "-i", str(avatar_path),
            "-vf", (
                f"drawtext="
                f"text='{speaker_name}':"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"fontsize=48:"
                f"fontcolor=white:"
                f"x=(w-text_w)/2:"
                f"y=50:"
                f"box=1:"
                f"boxcolor=black@0.6:"
                f"boxborderw=10"
            ),
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            str(output_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error creating segment: {e.stderr}")
            raise

    def _render_video(
        self,
        concat_file: Path,
        audio_path: Path,
        output_path: Path
    ) -> None:
        """
        Render final video by concatenating segments and adding audio.

        Args:
            concat_file: Path to concat file
            audio_path: Path to audio file
            output_path: Output video path
        """
        # FFmpeg command to concatenate video segments and add audio
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",  # Match shortest stream (video or audio)
            str(output_path)
        ]

        logger.info(f"Running FFmpeg to create final video...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Video rendering complete")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to render video: {e.stderr}")

    def cleanup_temp_files(self) -> None:
        """Clean up temporary segment files."""
        logger.info("Cleaning up temporary video files...")

        # Remove segment videos
        for seg_file in self.work_dir.glob("segment_*.mp4"):
            seg_file.unlink()

        # Remove concat file
        concat_file = self.work_dir / "concat_list.txt"
        if concat_file.exists():
            concat_file.unlink()

        logger.info("Cleanup complete")
