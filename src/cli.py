"""
Command-line interface for Synthetic Newsroom.
"""
from datetime import datetime
from pathlib import Path
import sys

import click

from .shared.logger import setup_logger
from .shared.settings import get_settings
from .workflows.daily_pipeline import DailyPipeline
from .workflows.backfill_pipeline import backfill_episodes
from .agents.character_initializer import CharacterInitializer

logger = setup_logger()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to config YAML file')
def cli(verbose, config):
    """Synthetic Newsroom - AI Podcast Generator"""
    # Setup logging
    if verbose:
        setup_logger(level="DEBUG")

    # Load settings
    config_path = Path(config) if config else None
    get_settings(reload=True, yaml_path=config_path)


@cli.command()
@click.option('--date', type=str, help='Date for episode (YYYY-MM-DD), defaults to today')
@click.option('--resume', type=click.Choice(['collect', 'nlp', 'debate', 'tts', 'mix', 'video', 'publish']),
              help='Resume from specific stage')
def run_daily(date, resume):
    """
    Run daily podcast generation pipeline.

    Generates a podcast episode for the specified date (or today).
    """
    try:
        # Parse date
        if date:
            episode_date = datetime.strptime(date, '%Y-%m-%d')
        else:
            episode_date = datetime.now()

        logger.info(f"Running daily pipeline for {episode_date.date()}")

        # Run pipeline
        pipeline = DailyPipeline(date=episode_date)
        audio_path = pipeline.run(resume_from=resume)

        logger.info("=" * 60)
        logger.info("SUCCESS! Podcast episode generated")
        logger.info(f"Episode ID: {pipeline.episode_id}")
        logger.info(f"Audio file: {audio_path}")
        logger.info("=" * 60)

        click.echo(f"\nPodcast generated successfully!")
        click.echo(f"Output: {audio_path}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--from-stage', type=click.Choice(['collect', 'nlp', 'debate', 'tts', 'mix', 'video', 'publish']),
              required=True, help='Stage to resume from')
@click.option('--date', type=str, required=True, help='Date of episode (YYYY-MM-DD)')
def resume(from_stage, date):
    """
    Resume pipeline from a specific stage.

    Useful for retrying failed pipelines or re-running specific stages.
    """
    try:
        episode_date = datetime.strptime(date, '%Y-%m-%d')

        logger.info(f"Resuming pipeline from '{from_stage}' for {episode_date.date()}")

        pipeline = DailyPipeline(date=episode_date)
        audio_path = pipeline.run(resume_from=from_stage)

        click.echo(f"\nPipeline resumed successfully!")
        click.echo(f"Output: {audio_path}")

    except Exception as e:
        logger.error(f"Resume failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
def backfill(start, end):
    """
    Generate episodes for a date range.

    Useful for creating historical episodes or catching up on missed days.
    """
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d')
        end_date = datetime.strptime(end, '%Y-%m-%d')

        if start_date > end_date:
            raise ValueError("Start date must be before end date")

        logger.info(f"Backfilling from {start_date.date()} to {end_date.date()}")

        episode_ids = backfill_episodes(start_date, end_date)

        click.echo(f"\nBackfill complete! Generated {len(episode_ids)} episodes")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


@cli.command()
def validate_config():
    """
    Validate configuration and dependencies.

    Checks:
    - Config files exist
    - API keys are set
    - ffmpeg is available
    - Directory structure
    """
    click.echo("Validating configuration...")

    settings = get_settings()
    errors = []
    warnings = []

    # Check config files
    config_file = settings.config_dir / "settings.yaml"
    if not config_file.exists():
        warnings.append(f"Config file not found: {config_file}")

    # Check API keys
    if not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY not set (required for full functionality)")

    # Check ffmpeg
    import shutil
    if not shutil.which("ffmpeg"):
        errors.append("ffmpeg not found in PATH (required for audio processing)")

    # Check data directories
    for dir_name in ["news_raw", "news_clean", "transcripts", "audio_stems", "episodes"]:
        dir_path = settings.data_dir / dir_name
        if not dir_path.exists():
            warnings.append(f"Data directory missing: {dir_path}")

    # Display results
    if errors:
        click.echo("\n❌ ERRORS:", err=True)
        for error in errors:
            click.echo(f"  - {error}", err=True)

    if warnings:
        click.echo("\n⚠️  WARNINGS:")
        for warning in warnings:
            click.echo(f"  - {warning}")

    if not errors and not warnings:
        click.echo("\n✅ Configuration valid!")
    elif errors:
        click.echo("\n❌ Validation failed")
        sys.exit(1)
    else:
        click.echo("\n⚠️  Validation passed with warnings")


@cli.command()
def info():
    """Show system and configuration information."""
    settings = get_settings()

    click.echo("=" * 60)
    click.echo("Synthetic Newsroom - System Information")
    click.echo("=" * 60)
    click.echo(f"\nProject Root: {settings.project_root}")
    click.echo(f"Config Dir:   {settings.config_dir}")
    click.echo(f"Data Dir:     {settings.data_dir}")
    click.echo(f"\nRSS Sources:  {len(settings.sources)}")
    click.echo(f"Voices:       {len(settings.voices)}")
    click.echo(f"Storage:      {settings.storage.driver}")
    click.echo(f"\nAPI Keys:")
    click.echo(f"  OpenAI:     {'✓' if settings.openai_api_key else '✗'}")
    click.echo(f"  Anthropic:  {'✓' if settings.anthropic_api_key else '✗'}")
    click.echo(f"  Google:     {'✓' if settings.google_api_key else '✗'}")
    click.echo("=" * 60)


@cli.command()
@click.option('--force', '-f', is_flag=True, help='Force regeneration even if characters exist')
def init_characters(force):
    """
    Initialize AI debate character personas.

    Each AI (ChatGPT, Gemini, Claude) will define their own debate character,
    including persona name, first-person pronoun, stance, and characteristics.

    This command only needs to be run once (or with --force to regenerate).
    """
    try:
        click.echo("Initializing AI character personas...")
        click.echo("=" * 60)

        initializer = CharacterInitializer()

        # Check if characters already exist
        existing = initializer.load_characters()
        if existing and not force:
            click.echo("\nCharacter configurations already exist:")
            click.echo("")
            for speaker, char in existing.items():
                click.echo(f"  {char['ai_name']} ({char['company']})")
                click.echo(f"    Persona: {char['persona_name']}")
                click.echo(f"    Stance:  {char['stance']}")
                click.echo(f"    Phrase:  「{char['catchphrase']}」")
                click.echo("")
            click.echo("Use --force to regenerate.")
            return

        # Initialize characters
        characters = initializer.initialize_all_characters(force=force)

        click.echo("\n✅ Character personas initialized successfully!")
        click.echo("")

        for speaker, char in characters.items():
            click.echo(f"  {char['ai_name']} ({char['company']})")
            click.echo(f"    Persona:  {char['persona_name']}")
            click.echo(f"    一人称:   {char['first_person']}")
            click.echo(f"    Stance:   {char['stance']}")
            click.echo(f"    特徴:     {char['characteristics']}")
            click.echo(f"    フレーズ: 「{char['catchphrase']}」")
            click.echo(f"    紹介:     {char['introduction_style']}")
            click.echo("")

        config_path = initializer.character_path
        click.echo(f"Configuration saved to: {config_path}")
        click.echo("\nThese characters will be used in all future debates!")

    except Exception as e:
        logger.error(f"Failed to initialize characters: {e}", exc_info=True)
        click.echo(f"\n❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
