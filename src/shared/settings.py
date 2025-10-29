"""
Settings management using Pydantic Settings.
Loads configuration from both .env and YAML files.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class VoiceConfig(BaseSettings):
    """Voice configuration for each speaker."""
    provider: Literal["mock", "elevenlabs", "gcloud"] = "mock"
    voice_id: str
    speed: float = 1.0
    pitch: Optional[float] = None


class RSSSourceConfig(BaseSettings):
    """RSS feed source configuration."""
    type: Literal["rss"] = "rss"
    url: str
    max_articles: int = 5


class AudioConfig(BaseSettings):
    """Audio mixing configuration."""
    target_lufs: float = -16.0
    peak_db: float = -1.0
    bgm_path: Optional[str] = None
    bgm_volume_db: float = -15.0


class StorageConfig(BaseSettings):
    """Storage configuration for episodes."""
    driver: Literal["local", "s3"] = "local"
    local_base: str = "data/episodes"
    public_base_url: str = "http://localhost:8080/podcast"
    # S3 settings (loaded from env)
    s3_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None


class VideoConfig(BaseSettings):
    """Video generation configuration."""
    enabled: bool = True
    width: int = 1920
    height: int = 1080
    fps: int = 30


class RSSConfig(BaseSettings):
    """Podcast RSS feed configuration."""
    site_title: str = "Synthetic Newsroom"
    site_link: str = "https://example.com"
    site_description: str = "AI daily debate podcast"
    language: str = "ja"
    author: str = "Synthetic Newsroom AI"
    image_url: Optional[str] = None


class Settings(BaseSettings):
    """Main settings class."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Keys (from .env)
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(None, alias="GOOGLE_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(None, alias="ELEVENLABS_API_KEY")
    google_application_credentials: Optional[str] = Field(
        None, alias="GOOGLE_APPLICATION_CREDENTIALS"
    )

    # S3/R2 (from .env)
    s3_endpoint: Optional[str] = Field(None, alias="S3_ENDPOINT")
    s3_access_key: Optional[str] = Field(None, alias="S3_ACCESS_KEY")
    s3_secret_key: Optional[str] = Field(None, alias="S3_SECRET_KEY")
    s3_bucket: Optional[str] = Field(None, alias="S3_BUCKET")

    # YAML-based config (loaded separately)
    sources: List[RSSSourceConfig] = []
    voices: Dict[str, VoiceConfig] = {}
    audio: AudioConfig = AudioConfig()
    storage: StorageConfig = StorageConfig()
    rss: RSSConfig = RSSConfig()
    video: VideoConfig = VideoConfig()

    # Runtime settings
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    config_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "configs")
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")

    @model_validator(mode='after')
    def set_google_credentials_env(self) -> 'Settings':
        """Set GOOGLE_APPLICATION_CREDENTIALS environment variable."""
        if self.google_application_credentials:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = (
                self.google_application_credentials
            )
        return self

    def load_yaml_config(self, yaml_path: Optional[Path] = None) -> None:
        """Load additional configuration from YAML file."""
        if yaml_path is None:
            yaml_path = self.config_dir / "settings.yaml"

        if not yaml_path.exists():
            return

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Parse sources
        if "sources" in data:
            self.sources = [RSSSourceConfig(**src) for src in data["sources"]]

        # Parse voices
        if "voices" in data:
            self.voices = {
                name: VoiceConfig(**config)
                for name, config in data["voices"].items()
            }

        # Parse audio config
        if "audio" in data:
            self.audio = AudioConfig(**data["audio"])

        # Parse storage config
        if "storage" in data:
            storage_data = data["storage"].copy()
            # Override with env vars if present
            if self.s3_endpoint:
                storage_data["s3_endpoint"] = self.s3_endpoint
            if self.s3_bucket:
                storage_data["s3_bucket"] = self.s3_bucket
            self.storage = StorageConfig(**storage_data)

        # Parse RSS config
        if "rss" in data:
            self.rss = RSSConfig(**data["rss"])


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(reload: bool = False, yaml_path: Optional[Path] = None) -> Settings:
    """
    Get or create the global settings instance.

    Args:
        reload: Force reload settings
        yaml_path: Path to YAML config file (defaults to configs/settings.yaml)

    Returns:
        Settings instance
    """
    global _settings

    if _settings is None or reload:
        _settings = Settings()
        _settings.load_yaml_config(yaml_path)

    return _settings
