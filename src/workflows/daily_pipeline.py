"""
Daily podcast generation pipeline.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..agents.debate_orchestrator import DebateOrchestrator
from ..audio.mix import AudioMixer
from ..collectors.article_extractor import ArticleExtractor
from ..collectors.rss import NewsArticle, RSSCollector
from ..nlp.summarize import ArticleSummarizer
from ..publish.episode_meta import EpisodeMeta, EpisodeMetaManager
from ..publish.rss_builder import build_podcast_rss
from ..publish.storage import create_storage_provider
from ..shared.logger import get_logger
from ..shared.settings import get_settings
from ..tts.mock_tts import create_tts_provider
from ..video.video_generator import VideoGenerator

logger = get_logger(__name__)


class DailyPipeline:
    """Orchestrate daily podcast generation."""

    def __init__(self, date: Optional[datetime] = None):
        """
        Initialize pipeline.

        Args:
            date: Date for this episode (defaults to today)
        """
        self.date = date or datetime.now()
        self.settings = get_settings()

        # Initialize components
        self.rss_collector = RSSCollector()
        self.article_extractor = ArticleExtractor()
        self.summarizer = ArticleSummarizer()
        self.debate_orchestrator = DebateOrchestrator(date=self.date)
        self.audio_mixer = AudioMixer(
            target_lufs=self.settings.audio.target_lufs,
            peak_db=self.settings.audio.peak_db,
            bgm_volume_db=self.settings.audio.bgm_volume_db
        )
        self.storage = create_storage_provider()
        self.meta_manager = EpisodeMetaManager(
            self.settings.data_dir / "metadata"
        )

        # Episode ID
        self.episode_id = f"episode_{self.date.strftime('%Y%m%d')}"

        # Working directories
        self.work_dir = self.settings.data_dir / "work" / self.episode_id
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def run(self, resume_from: Optional[str] = None) -> Path:
        """
        Run complete pipeline.

        Args:
            resume_from: Stage to resume from (collect, nlp, debate, tts, mix, video, publish)

        Returns:
            Path to generated podcast file
        """
        logger.info(f"Starting daily pipeline for {self.episode_id}")

        # Stage 1: Collect news
        if not resume_from or resume_from == "collect":
            articles = self._collect_news()
            self._save_checkpoint("articles", articles)
        else:
            articles = self._load_checkpoint("articles")

        # Stage 2: NLP processing
        if not resume_from or resume_from in ["collect", "nlp"]:
            topic = self._process_nlp(articles)
            self._save_checkpoint("topic", topic)
        else:
            topic = self._load_checkpoint("topic")

        # Stage 3: Generate debate script
        if not resume_from or resume_from in ["collect", "nlp", "debate"]:
            script = self._generate_debate(topic)
            self._save_checkpoint("script", script)
        else:
            script = self._load_checkpoint("script")

        # Stage 4: Text-to-Speech
        if not resume_from or resume_from in ["collect", "nlp", "debate", "tts"]:
            audio_files = self._synthesize_speech(script)
            self._save_checkpoint("audio_files", audio_files)
        else:
            audio_files = self._load_checkpoint("audio_files")

        # Stage 5: Mix audio
        if not resume_from or resume_from in ["collect", "nlp", "debate", "tts", "mix"]:
            mixed_audio = self._mix_audio(audio_files)
        else:
            mixed_audio = self.work_dir / f"{self.episode_id}.mp3"

        # Stage 6: Generate video (optional)
        video_path = None
        if self.settings.video.enabled:
            if not resume_from or resume_from in ["collect", "nlp", "debate", "tts", "mix", "video"]:
                video_path = self._generate_video(script, mixed_audio)
                self._save_checkpoint("video_path", str(video_path))
            else:
                saved_path = self._load_checkpoint("video_path")
                video_path = Path(saved_path) if saved_path else None

        # Stage 7: Publish
        episode_meta = self._publish(
            mixed_audio,
            script.title,
            script.topic_summary,
            articles,
            int(script.total_duration_sec),
            video_path=video_path
        )

        logger.info(f"Pipeline complete! Episode: {episode_meta.episode_id}")
        logger.info(f"Audio URL: {episode_meta.audio_url}")

        return Path(mixed_audio)

    def _collect_news(self) -> List[NewsArticle]:
        """Stage 1: Collect news articles."""
        logger.info("Stage 1: Collecting news articles")

        all_articles = []

        # Collect from all configured sources
        for source_config in self.settings.sources:
            try:
                articles = self.rss_collector.fetch_feed(
                    source_config.url,
                    max_articles=source_config.max_articles
                )
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Failed to fetch from {source_config.url}: {e}")
                continue

        if not all_articles:
            raise RuntimeError("No articles collected from any source")

        # Extract full content
        articles_with_content = self.article_extractor.extract_batch(all_articles)

        logger.info(f"Collected {len(articles_with_content)} articles")
        return articles_with_content

    def _process_nlp(self, articles: List[NewsArticle]):
        """Stage 2: NLP processing."""
        logger.info("Stage 2: NLP processing")

        # Create debate topic from articles
        topic = self.summarizer.create_debate_topic(articles)

        logger.info(f"Created topic: {topic.title}")
        return topic

    def _generate_debate(self, topic):
        """Stage 3: Generate debate script."""
        logger.info("Stage 3: Generating debate script")

        script = self.debate_orchestrator.generate_script(topic)

        # Save transcript
        transcript_path = self.work_dir / "transcript.json"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(script.to_json())

        logger.info(f"Generated script with {len(script.lines)} lines")
        return script

    def _synthesize_speech(self, script) -> List[Path]:
        """Stage 4: Text-to-Speech."""
        logger.info("Stage 4: Synthesizing speech")

        # Create TTS providers for each speaker based on settings
        tts_providers = {}
        for speaker, voice_config in self.settings.voices.items():
            tts_providers[speaker] = create_tts_provider(
                provider_type=voice_config.provider,
                voice_name=voice_config.voice_id,
                speaking_rate=voice_config.speed,
                pitch=voice_config.pitch or 0.0
            )

        # Synthesize all lines with speaker-specific providers
        audio_dir = self.work_dir / "audio_stems"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_files = []

        for i, line in enumerate(script.lines):
            output_path = audio_dir / f"{i:03d}_{line.speaker}.wav"
            provider = tts_providers.get(line.speaker)
            if provider is None:
                logger.warning(
                    f"No TTS provider for speaker '{line.speaker}', "
                    f"using default"
                )
                provider = tts_providers.get('host') or create_tts_provider(
                    provider_type="mock"
                )
            provider.synthesize(line.text, line.speaker, output_path)
            audio_files.append(output_path)

        logger.info(f"Synthesized {len(audio_files)} audio segments")
        return audio_files

    def _mix_audio(self, audio_files: List[Path]) -> Path:
        """Stage 5: Mix audio."""
        logger.info("Stage 5: Mixing audio")

        output_path = self.work_dir / f"{self.episode_id}.mp3"

        # Get BGM path if configured
        bgm_path = None
        if self.settings.audio.bgm_path:
            bgm_path = self.settings.project_root / self.settings.audio.bgm_path
            if not bgm_path.exists():
                logger.warning(f"BGM file not found: {bgm_path}")
                bgm_path = None

        # Mix
        self.audio_mixer.mix_podcast(
            voice_files=audio_files,
            output_path=output_path,
            bgm_path=bgm_path
        )

        logger.info(f"Mixed audio saved: {output_path}")
        return output_path

    def _generate_video(self, script, audio_path: Path) -> Path:
        """Stage 6: Generate video (optional)."""
        logger.info("Stage 6: Generating video")

        # Load character configurations
        import yaml
        character_path = self.settings.config_dir / "characters.yaml"
        with open(character_path, 'r', encoding='utf-8') as f:
            characters = yaml.safe_load(f) or {}

        # Create video generator
        video_work_dir = self.work_dir / "video"
        video_gen = VideoGenerator(video_work_dir, characters)

        # Audio stems directory
        audio_stems_dir = self.work_dir / "audio_stems"

        # Generate video
        video_path = self.work_dir / f"{self.episode_id}.mp4"
        video_gen.generate_video(
            script,
            audio_path,
            video_path,
            audio_stems_dir=audio_stems_dir
        )

        logger.info(f"Video generated: {video_path}")
        return video_path

    def _publish(
        self,
        audio_path: Path,
        title: str,
        description: str,
        source_articles: List[NewsArticle],
        duration_seconds: int,
        video_path: Optional[Path] = None
    ) -> EpisodeMeta:
        """Stage 7: Publish episode."""
        logger.info("Stage 7: Publishing episode")

        # Upload audio file
        remote_key = f"episodes/{self.episode_id}.mp3"
        audio_url = self.storage.upload(audio_path, remote_key)

        # Upload video file if available
        video_url = None
        if video_path and video_path.exists():
            video_remote_key = f"episodes/{self.episode_id}.mp4"
            video_url = self.storage.upload(video_path, video_remote_key)
            logger.info(f"Video uploaded: {video_url}")

        # Get file size
        file_size = audio_path.stat().st_size

        # Create episode metadata
        episode_meta = EpisodeMeta(
            episode_id=self.episode_id,
            title=f"{title} - {self.date.strftime('%Y年%m月%d日')}",
            description=description,
            pub_date=self.date,
            audio_url=audio_url,
            audio_file_size=file_size,
            duration_seconds=duration_seconds,
            source_articles=[a.url for a in source_articles if a.url],
            video_url=video_url
        )

        # Save metadata
        self.meta_manager.save_episode(episode_meta)

        # Rebuild RSS feed
        self._rebuild_rss()

        logger.info(f"Published episode: {episode_meta.episode_id}")
        return episode_meta

    def _rebuild_rss(self) -> None:
        """Rebuild RSS feed with all episodes."""
        logger.info("Rebuilding RSS feed")

        # Get all episodes (sorted newest first)
        episodes = self.meta_manager.list_episodes(limit=50)  # Keep last 50 episodes

        # Build RSS
        rss_path = self.settings.data_dir / "podcast.xml"
        build_podcast_rss(episodes, rss_path)

        logger.info(f"RSS feed updated: {rss_path}")

    def _save_checkpoint(self, name: str, data) -> None:
        """Save pipeline checkpoint."""
        import pickle
        checkpoint_path = self.work_dir / f"checkpoint_{name}.pkl"
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(data, f)
        logger.debug(f"Saved checkpoint: {name}")

    def _load_checkpoint(self, name: str):
        """Load pipeline checkpoint."""
        import pickle
        checkpoint_path = self.work_dir / f"checkpoint_{name}.pkl"
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {name}")
        with open(checkpoint_path, 'rb') as f:
            data = pickle.load(f)
        logger.debug(f"Loaded checkpoint: {name}")
        return data
