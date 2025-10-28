"""
Retry utilities using tenacity.
"""
from typing import Any, Callable

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log
)
import logging

from .logger import get_logger

logger = get_logger(__name__)


def retry_on_network_error(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10
) -> Callable:
    """
    Decorator for retrying on network-related errors.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorator function
    """
    return retry(
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            OSError,
        )),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )


def retry_on_api_error(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 30
) -> Callable:
    """
    Decorator for retrying on API-related errors.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Decorator function
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG),
        reraise=True
    )
