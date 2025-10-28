"""
Simple structured logging using rich.
"""
import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


# Global console instance
console = Console()


def setup_logger(
    name: str = "synthetic-newsroom",
    level: str = "INFO",
    rich_tracebacks: bool = True
) -> logging.Logger:
    """
    Setup a logger with rich formatting.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rich_tracebacks: Enable rich tracebacks

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=rich_tracebacks,
                tracebacks_show_locals=False,
                show_time=True,
                show_path=False
            )
        ]
    )

    logger = logging.getLogger(name)
    return logger


# Default logger instance
logger = setup_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (uses default if None)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(name)
    return logger
