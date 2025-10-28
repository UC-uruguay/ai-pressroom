"""
Test settings loading and configuration.
"""
import pytest
from pathlib import Path
from src.shared.settings import Settings, get_settings


def test_settings_default_values():
    """Test that settings have sensible defaults."""
    settings = Settings()

    assert settings.project_root.exists()
    assert settings.config_dir.exists()
    assert settings.data_dir.exists()


def test_settings_singleton():
    """Test that get_settings returns same instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_settings_reload():
    """Test that settings can be reloaded."""
    settings1 = get_settings()
    settings2 = get_settings(reload=True)

    # Should be different instances after reload
    assert settings1 is not settings2
