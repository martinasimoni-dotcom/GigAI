"""
Unit tests for normalizer module (PROC-01, PROC-02).
Stubs are collectable before implementation; tests skip until normalizer.py has content.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_IMPL_PATH = (
    Path(__file__).parent.parent.parent
    / "src" / "system" / "data_processing" / "normalizer.py"
)
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="normalizer.py not yet implemented"
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set env vars and evict settings-dependent modules before each test."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    for mod in [
        "src.system.data_processing.normalizer",
        "src.system.data_processing",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)


def _make_raw_event(text: str = "change third-floor windows from aluminum to wood, 12 units"):
    from src.shared.models.events import RawEvent
    return RawEvent(event_id="e-test-01", source="fireflies", raw_payload={"text": text})


_HAIKU_VALID = (
    '{"event_id":"e-test-01","source":"fireflies","event_type":"material_change",'
    '"material_original":"aluminum","material_new":"wood","location":"3rd floor",'
    '"quantity":12,"people":[],"deadlines":[],'
    '"summary":"Change 12 third-floor windows from aluminum to wood.",'
    '"confidence":85,"review_required":false,"estimated_cost":null}'
)

_HAIKU_LOW_CONFIDENCE = (
    '{"event_id":"e-test-01","source":"fireflies","event_type":"material_change",'
    '"material_original":null,"material_new":null,"location":null,'
    '"quantity":null,"people":[],"deadlines":[],'
    '"summary":"Unclear material change event.",'
    '"confidence":60,"review_required":false,"estimated_cost":null}'
)


# --- PROC-02: normalize_event() happy path ---

def test_normalize_event_returns_normalized_event():
    """normalize_event() returns NormalizedEvent with correct fields for demo scenario."""
    from src.system.data_processing import normalizer
    raw = _make_raw_event()
    with patch.object(normalizer, "call_haiku", return_value=_HAIKU_VALID):
        result = normalizer.normalize_event(raw)
    assert result.event_type == "material_change"
    assert result.material_original == "aluminum"
    assert result.material_new == "wood"
    assert result.location == "3rd floor"
    assert result.quantity == 12
    assert result.confidence == 85
    assert result.review_required is False


def test_normalize_event_low_confidence_sets_review_required():
    """confidence < 70 must set review_required=True (not reject)."""
    from src.system.data_processing import normalizer
    raw = _make_raw_event()
    with patch.object(normalizer, "call_haiku", return_value=_HAIKU_LOW_CONFIDENCE):
        result = normalizer.normalize_event(raw)
    assert result.confidence == 60
    assert result.review_required is True


def test_normalize_event_retries_on_validation_error(monkeypatch):
    """Pydantic validation failure triggers up to 3 retries before raising."""
    from src.system.data_processing import normalizer

    bad_json = '{"event_id":"e-test-01","source":"fireflies","event_type":"mc","summary":""}'
    call_count = {"n": 0}

    def _haiku_side_effect(*args, **kwargs):
        call_count["n"] += 1
        return bad_json

    raw = _make_raw_event()
    with patch.object(normalizer, "call_haiku", side_effect=_haiku_side_effect):
        with pytest.raises(Exception):
            normalizer.normalize_event(raw)
    assert call_count["n"] >= 2  # at least 2 attempts (tenacity retries)


# --- PROC-01: normalization prompt file content ---

def test_normalization_prompt_file_exists():
    """config/prompts/normalization.txt must exist and contain key field names."""
    prompt_path = (
        Path(__file__).parent.parent.parent / "config" / "prompts" / "normalization.txt"
    )
    assert prompt_path.exists(), "normalization.txt not found"
    content = prompt_path.read_text()
    assert "material_original" in content or "material" in content
    assert "location" in content
    assert "quantity" in content
    assert "summary" in content
    assert "confidence" in content
