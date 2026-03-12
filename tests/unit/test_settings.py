"""
Settings tests (FOUND-10): verify config/settings.py loads from env and fails fast on missing keys.

The Settings class has a module-level `settings = Settings()` singleton. This means importing
the module with missing env vars WILL raise ValidationError — which is exactly what we want to test.
We wrap the import in pytest.raises to capture this behavior.
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


def test_settings_fails_without_anthropic_key(monkeypatch):
    """Importing config.settings must fail if ANTHROPIC_API_KEY is missing."""
    from pydantic import ValidationError

    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    _clear_settings_module()

    # The module-level `settings = Settings()` raises ValidationError on import
    with pytest.raises((ValidationError, Exception)):
        import config.settings  # noqa: F401


def test_settings_fails_without_voyage_key(monkeypatch):
    """Importing config.settings must fail if VOYAGE_API_KEY is missing."""
    from pydantic import ValidationError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    _clear_settings_module()

    with pytest.raises((ValidationError, Exception)):
        import config.settings  # noqa: F401


def test_settings_fails_without_database_url(monkeypatch):
    """Importing config.settings must fail if DATABASE_URL is missing."""
    from pydantic import ValidationError

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    _clear_settings_module()

    with pytest.raises((ValidationError, Exception)):
        import config.settings  # noqa: F401
