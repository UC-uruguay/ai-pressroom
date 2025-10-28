"""
Backfill pipeline for generating historical episodes.

TODO: Implement backfill functionality
- Generate episodes for past dates
- Fetch historical news (if available)
- Process in batch
"""
from datetime import datetime, timedelta
from typing import List

from .daily_pipeline import DailyPipeline
from ..shared.logger import get_logger

logger = get_logger(__name__)


def backfill_episodes(start_date: datetime, end_date: datetime) -> List[str]:
    """
    Generate episodes for a date range.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of generated episode IDs

    Note:
        This is a simple implementation. For production:
        - Add parallel processing
        - Handle failures gracefully
        - Skip existing episodes
        - Validate date ranges
    """
    logger.info(f"Backfilling episodes from {start_date} to {end_date}")

    current_date = start_date
    episode_ids = []

    while current_date <= end_date:
        try:
            logger.info(f"Generating episode for {current_date.date()}")
            pipeline = DailyPipeline(date=current_date)
            pipeline.run()
            episode_ids.append(pipeline.episode_id)

        except Exception as e:
            logger.error(f"Failed to generate episode for {current_date.date()}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"Backfill complete: generated {len(episode_ids)} episodes")
    return episode_ids
