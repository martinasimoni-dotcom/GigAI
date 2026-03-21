"""
Settings tests (FOUND-10): verify config/settings.py loads from env.

Settings now use defaults for all fields so the app can start
without a full .env. These tests verify loading works correctly.
"""
import sys

import pytest


def _clear_settings_module():
    """Remove config.settings from sys.modules to force re-import."""
    for key in list(sys.modules.keys()):
        if key == "config.settings" or key.startswith("config.settings."):
            del sys.modules[key]


def test_settings_loads_from_env(monkeypatch):
    """Settings class must load anthropic_api_key from environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")

    _clear_settings_module()
    from config.settings import Settings

    s = Settings(_env_file=None)
    assert s.anthropic_api_key == "test-key"
    assert s.voyage_api_key == "test-key"


def test_settings_defaults_without_keys(monkeypatch):
    """Settings defaults to empty strings when keys are missing — no crash."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    _clear_settings_module()
    from config.settings import Settings

    s = Settings(_env_file=None)
    assert s.anthropic_api_key == ""
    assert s.voyage_api_key == ""
    assert s.database_url == ""


def test_settings_threshold_defaults(monkeypatch):
    """Pipeline thresholds have correct default values."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")

    _clear_settings_module()
    from config.settings import Settings

    s = Settings(_env_file=None)
    assert s.confidence_accept_threshold == 80.0
    assert s.confidence_reject_threshold == 50.0
    assert s.poll_interval_seconds == 60
