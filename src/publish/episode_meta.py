"""
Episode metadata management.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json


@dataclass
class EpisodeMeta:
    """Metadata for a podcast episode."""
    episode_id: str
    title: str
    description: str
    pub_date: datetime
    audio_url: str
    audio_file_size: int
    duration_seconds: int
    source_articles: List[str]  # Article URLs
    transcript_path: Optional[str] = None
    video_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['pub_date'] = self.pub_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "EpisodeMeta":
        """Create from dictionary."""
        data['pub_date'] = datetime.fromisoformat(data['pub_date'])
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "EpisodeMeta":
        """Load from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        """Save to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: Path) -> "EpisodeMeta":
        """Load from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())


class EpisodeMetaManager:
    """Manage episode metadata."""

    def __init__(self, meta_dir: Path):
        """
        Initialize manager.

        Args:
            meta_dir: Directory to store metadata files
        """
        self.meta_dir = meta_dir
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def save_episode(self, episode: EpisodeMeta) -> Path:
        """
        Save episode metadata.

        Args:
            episode: EpisodeMeta to save

        Returns:
            Path to saved metadata file
        """
        meta_path = self.meta_dir / f"{episode.episode_id}.json"
        episode.save(meta_path)
        return meta_path

    def load_episode(self, episode_id: str) -> EpisodeMeta:
        """
        Load episode metadata.

        Args:
            episode_id: Episode ID

        Returns:
            EpisodeMeta

        Raises:
            FileNotFoundError: If episode not found
        """
        meta_path = self.meta_dir / f"{episode_id}.json"
        return EpisodeMeta.load(meta_path)

    def list_episodes(self, limit: Optional[int] = None) -> List[EpisodeMeta]:
        """
        List all episodes, sorted by publication date (newest first).

        Args:
            limit: Maximum number of episodes to return

        Returns:
            List of EpisodeMeta
        """
        episodes = []

        for meta_file in self.meta_dir.glob("*.json"):
            try:
                episode = EpisodeMeta.load(meta_file)
                episodes.append(episode)
            except Exception as e:
                # Skip invalid metadata files
                continue

        # Sort by publication date (newest first)
        episodes.sort(key=lambda e: e.pub_date, reverse=True)

        if limit:
            episodes = episodes[:limit]

        return episodes
