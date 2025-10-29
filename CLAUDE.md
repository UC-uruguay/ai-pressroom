# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Synthetic Newsroom (AI Pressroom)** is a daily AI podcast generation system that collects news from RSS feeds, orchestrates debates between multiple AI personalities (ChatGPT, Gemini, Claude), synthesizes speech, and publishes episodes as a podcast RSS feed.

The system is designed as a fully automated pipeline that can run daily via GitHub Actions or be triggered manually.

## Development Commands

### Setup and Installation
```bash
make setup          # Initial setup: creates venv, installs deps, copies configs
make install        # Install Python dependencies only
make validate       # Validate configuration and check dependencies
```

### Running the Pipeline
```bash
# Run full pipeline
python -m src.cli run-daily                    # Generate today's episode
python -m src.cli run-daily --date 2025-01-15  # Generate for specific date

# Resume from failed stage
python -m src.cli resume --from-stage tts --date 2025-01-15

# Backfill episodes
python -m src.cli backfill --start 2025-01-01 --end 2025-01-07

# Utilities
python -m src.cli validate-config  # Check configuration
python -m src.cli info             # Show system info
```

### Testing and Quality
```bash
make test           # Run pytest with coverage
make lint           # Run flake8 and mypy
make format         # Format with black and isort
make clean          # Clean temporary files
```

### Serving Locally
```bash
make serve          # Start HTTP server on http://localhost:8080
```

## Architecture Overview

### Pipeline Stages (DailyPipeline)

The pipeline in `src/workflows/daily_pipeline.py` orchestrates six sequential stages:

1. **collect**: RSS collection → article extraction (full text via BeautifulSoup)
2. **nlp**: Summarization → debate topic generation
3. **debate**: Multi-agent LLM calls → structured script with speaker/text/timing
4. **tts**: Text-to-speech synthesis for each line (mock by default)
5. **mix**: Audio concatenation + BGM + loudness normalization (FFmpeg)
6. **publish**: Storage upload + episode metadata + RSS feed generation

Each stage saves checkpoints as pickle files in `data/work/episode_YYYYMMDD/checkpoint_*.pkl`, enabling resume functionality.

### Configuration System

**Two-layer configuration:**
- `.env` file: API keys, S3 credentials (loaded via pydantic-settings)
- `configs/settings.yaml`: RSS sources, voice configs, audio settings, RSS metadata

The `Settings` class in `src/shared/settings.py` loads both and provides a singleton via `get_settings()`.

Key settings:
- `sources`: List of RSS feeds with `url` and `max_articles`
- `voices`: Dict mapping speaker names to TTS provider/voice_id/speed
- `audio`: Loudness normalization params (LUFS, peak dB, BGM volume)
- `storage`: Driver ("local" or "s3") and URL configuration
- `rss`: Podcast metadata (title, description, author, image)

### Core Abstractions

**TTSProvider** (`src/tts/base.py`):
- Abstract interface for swappable TTS backends
- `synthesize(text, speaker, output_path)` → returns Path to WAV file
- Implementations: `MockTTS` (default, generates beeps), `ElevenLabsTTS` (stub), `GCloudTTS` (stub)

**StorageProvider** (`src/publish/storage.py`):
- Abstract interface for episode storage
- `upload(local_path, remote_key)` → returns public URL
- `LocalStorageProvider`: Copies to `data/episodes/` and constructs URLs with `public_base_url`
- `S3StorageProvider`: Stub with TODO comments (boto3 implementation needed)

**DebateOrchestrator** (`src/agents/debate_orchestrator.py`):
- Manages multi-turn debate script generation
- Loads system prompts from `src/agents/prompts/system_{chatgpt,gemini,claude}.txt`
- Generates `DebateScript` with structured `DebateLine[]` (speaker, text, duration, pause)
- Uses appropriate LLM client based on speaker (OpenAI for ChatGPT, Anthropic for Claude)
- Fallback responses when API clients are unavailable

### Audio Processing

**Loudness Normalization** (`src/audio/loudness.py`):
- Uses FFmpeg's `loudnorm` filter for broadcast-standard audio
- Two-pass normalization: first pass analyzes, second pass applies
- Target: -16 LUFS (Spotify/podcast standard)

**AudioMixer** (`src/audio/mix.py`):
- Concatenates voice stems with pauses
- Mixes with BGM (if configured) at specified volume offset
- Applies loudness normalization
- Outputs MP3 with proper encoding

### Episode Metadata and RSS

**EpisodeMetaManager** (`src/publish/episode_meta.py`):
- Stores episode metadata as JSON files in `data/metadata/`
- Each episode has: ID, title, description, pub_date, audio_url, duration, source articles

**RSS Builder** (`src/publish/rss_builder.py`):
- Generates RSS 2.0 feed at `data/podcast.xml`
- Includes all episode metadata with proper enclosure tags
- Compatible with Spotify for Podcasters and other podcast platforms

## Important Implementation Notes

### TTS Default Behavior
By default, the system uses **MockTTS** which generates test beeps instead of real speech. This allows testing the full pipeline without TTS API costs or dependencies.

To enable real TTS:
1. Implement `src/tts/elevenlabs_tts.py` or `src/tts/gcloud_tts.py`
2. Update `configs/settings.yaml` to set `voices.{speaker}.provider` to "elevenlabs" or "gcloud"
3. Add corresponding API keys to `.env`

### S3 Storage Not Implemented
The `S3StorageProvider` class exists but raises `NotImplementedError`. To implement:
1. Install boto3: `pip install boto3`
2. Implement `upload()` method using boto3's `upload_file()`
3. Set `ACL='public-read'` and appropriate content type
4. Handle errors and optionally implement multipart upload for large files

### LLM Fallbacks
The debate orchestrator gracefully handles missing API keys:
- If a speaker's LLM is unavailable, uses generic fallback responses
- This allows testing with only one LLM provider (e.g., OpenAI only)

### Data Directory Structure
```
data/
├── work/                    # Working directories per episode
│   └── episode_YYYYMMDD/
│       ├── checkpoint_*.pkl # Pipeline checkpoints
│       ├── audio_stems/     # Individual TTS outputs
│       └── episode_*.mp3    # Final mixed audio
├── metadata/                # Episode JSON metadata
├── episodes/                # Published episodes (local storage)
└── podcast.xml              # RSS feed
```

## Testing Strategy

Tests are in `tests/` and use pytest. Current coverage includes:
- Configuration loading and validation
- RSS feed generation and schema validation
- Debate script JSON serialization

Run tests with `make test` or `pytest tests/ -v`.

Mark slow tests with `@pytest.mark.slow` and integration tests with `@pytest.mark.integration`.

## GitHub Actions Integration

`.github/workflows/daily.yml` runs the pipeline daily at 6:00 UTC (15:00 JST).

Required secrets:
- `OPENAI_API_KEY` (required)
- `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` (optional)
- `ELEVENLABS_API_KEY` (if using ElevenLabs TTS)
- S3 credentials (if using S3 storage)

## Coding Standards

**IMPORTANT: All code in this repository must strictly adhere to the Python coding standards defined in [CODING_RULE.md](./CODING_RULE.md).**

Key requirements:
- Follow PEP 8 style guidelines (enforced by flake8)
- Use type hints for all function signatures
- Write docstrings for all public modules, classes, and functions
- Format code with Black and isort (run `make format`)
- Ensure all tests pass before committing (run `make test`)

Before submitting any code:
1. Run `make format` to auto-format code
2. Run `make lint` to check for style violations and type errors
3. Run `make test` to ensure all tests pass
4. Review [CODING_RULE.md](./CODING_RULE.md) for detailed guidelines

The CI pipeline will automatically enforce these standards. Pull requests that do not comply will be rejected.

## Development Guidelines

### Adding New TTS Providers
1. Create new class inheriting from `TTSProvider` in `src/tts/`
2. Implement `synthesize(text, speaker, output_path)` method
3. Update `create_tts_provider()` factory in `src/tts/mock_tts.py`
4. Add configuration to `VoiceConfig.provider` enum in `src/shared/settings.py`

### Adding New LLM Agents
1. Add system prompt to `src/agents/prompts/system_{name}.txt`
2. Update `SpeakerType` enum in `src/agents/debate_orchestrator.py`
3. Implement API call method (similar to `_call_openai()` or `_call_anthropic()`)
4. Add speaker to voice configuration in `configs/settings.yaml`

### Extending Storage Backends
1. Create new class inheriting from `StorageProvider`
2. Implement `upload()` and `get_url()` methods
3. Update `create_storage_provider()` factory in `src/publish/storage.py`

### Pipeline Stage Modification
If adding or modifying pipeline stages:
1. Update `DailyPipeline.run()` in `src/workflows/daily_pipeline.py`
2. Add checkpoint save/load logic
3. Update `resume_from` choices in `src/cli.py`
4. Update documentation in README.md

## Common Issues

### FFmpeg Not Found
The system requires FFmpeg for audio processing. Install with:
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Verify: `make validate`

### API Rate Limits
If hitting LLM API rate limits during debate generation:
- The `@retry_on_api_error` decorator in `src/agents/debate_orchestrator.py` handles transient errors
- Consider implementing exponential backoff in `src/shared/retry.py`

### Large Audio Files
For episodes longer than 10 minutes, consider:
- Implementing S3 storage (local filesystem works but isn't ideal for production)
- Enabling multipart upload for better reliability
- Adjusting `target_duration_min` in debate generation
