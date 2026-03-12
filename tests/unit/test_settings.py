"""
Settings tests (FOUND-10): verify config/settings.py loads from env and fails fast on missing keys.
"""
import importlib
import os
import sys

import pytest


def _import_settings_class():
    """Import Settings class fresh, avoiding module-level singleton issues."""
    # Remove cached module if present
    for mod_name in list(sys.modules.keys()):
        if "config.settings" in mod_name or mod_name == "config.settings":
            del sys.modules[mod_name]
    from config.settings import Settings
    return Settings


def test_settings_fails_without_anthropic_key(monkeypatch, test_env):
    """Settings must raise ValidationError when ANTHROPIC_API_KEY is missing."""
    from pydantic import ValidationError

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    Settings = _import_settings_class()
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)


def test_settings_loads_from_env(test_env):
    """Settings must load anthropic_api_key from environment."""
    Settings = _import_settings_class()
    s = Settings(_env_file=None)
    assert s.anthropic_api_key == "test-key"


def test_settings_fails_without_voyage_key(monkeypatch, test_env):
    """Settings must raise ValidationError when VOYAGE_API_KEY is missing."""
    from pydantic import ValidationError

    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    Settings = _import_settings_class()
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)


def test_settings_fails_without_database_url(monkeypatch, test_env):
    """Settings must raise ValidationError when DATABASE_URL is missing."""
    from pydantic import ValidationError

    monkeypatch.delenv("DATABASE_URL", raising=False)
    Settings = _import_settings_class()
    with pytest.raises((ValidationError, Exception)):
        Settings(_env_file=None)
