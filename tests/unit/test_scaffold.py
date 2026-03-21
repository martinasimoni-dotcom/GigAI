"""
Scaffold tests (FOUND-01): verify requirements.txt and .env.example contents.
"""
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def test_requirements_no_openai():
    """requirements.txt must NOT contain the openai package."""
    req_file = PROJECT_ROOT / "requirements.txt"
    contents = req_file.read_text(encoding="utf-8")
    assert "openai" not in contents.lower(), "openai must not appear in requirements.txt"


def test_requirements_has_anthropic():
    """requirements.txt must contain anthropic."""
    req_file = PROJECT_ROOT / "requirements.txt"
    contents = req_file.read_text(encoding="utf-8")
    assert "anthropic" in contents.lower()


def test_requirements_has_voyageai():
    """requirements.txt must contain voyageai."""
    req_file = PROJECT_ROOT / "requirements.txt"
    contents = req_file.read_text(encoding="utf-8")
    assert "voyageai" in contents.lower()


def test_requirements_has_pgvector():
    """requirements.txt must contain pgvector."""
    req_file = PROJECT_ROOT / "requirements.txt"
    contents = req_file.read_text(encoding="utf-8")
    assert "pgvector" in contents.lower()


def test_requirements_has_pydantic_settings():
    """requirements.txt must contain pydantic-settings."""
    req_file = PROJECT_ROOT / "requirements.txt"
    contents = req_file.read_text(encoding="utf-8")
    assert "pydantic-settings" in contents.lower()


def test_env_example_exists():
    """.env.example must exist at the project root."""
    env_file = PROJECT_ROOT / ".env.example"
    assert env_file.exists(), ".env.example does not exist at project root"


def test_env_example_has_anthropic_key():
    """.env.example must reference ANTHROPIC_API_KEY."""
    env_file = PROJECT_ROOT / ".env.example"
    contents = env_file.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in contents
