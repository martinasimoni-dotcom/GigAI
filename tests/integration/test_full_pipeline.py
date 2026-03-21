"""
Integration tests — Full pipeline from webhook ingestion to proposal generation.
Requires: .env with ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL
Run: pytest tests/integration/test_full_pipeline.py -m integration -v
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # Must precede src.* imports

import pytest  # noqa: E402
from unittest.mock import patch  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.requires_api, pytest.mark.requires_db]

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestWebhookIngestion:
    """Integration tests for webhook ingestion endpoints using real FastAPI app."""

    def test_fireflies_webhook_accepts_demo_transcript(self):
        """POST /webhooks/fireflies with demo transcript fixture returns 200 OK."""
        from fastapi.testclient import TestClient
        from src.main import app  # lazy import — settings already loaded by load_dotenv() above

        fixture_path = FIXTURES_DIR / "sample_transcript.json"
        payload = json.loads(fixture_path.read_text())

        with patch("src.input.pubsub.publish_event", return_value="msg-integration-001"):
            client = TestClient(app)
            response = client.post("/webhooks/fireflies", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_acc_webhook_accepts_demo_event(self):
        """POST /webhooks/acc with demo ACC event fixture returns 200 OK."""
        from fastapi.testclient import TestClient
        from src.main import app  # lazy import

        fixture_path = FIXTURES_DIR / "sample_acc_event.json"
        payload = json.loads(fixture_path.read_text())

        with patch("src.input.pubsub.publish_event", return_value="msg-integration-002"):
            client = TestClient(app)
            response = client.post("/webhooks/acc", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"

    def test_normalizer_produces_valid_normalized_event(self):
        """
        Call normalize_event() directly with the demo transcript fixture.
        Requires a real Anthropic API key (sk-ant- prefix).
        Skipped when ANTHROPIC_API_KEY is absent or a test placeholder.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key.startswith("sk-ant-"):
            pytest.skip(
                "ANTHROPIC_API_KEY not set or is a test placeholder — "
                "real Anthropic credentials required for normalizer integration test"
            )

        from src.shared.models.events import RawEvent
        from src.system.data_processing.normalizer import normalize_event

        fixture_path = FIXTURES_DIR / "sample_transcript.json"
        raw_payload = json.loads(fixture_path.read_text())

        raw_event = RawEvent(
            event_id="integration-test-001",
            source="fireflies",
            raw_payload=raw_payload,
        )

        normalized = normalize_event(raw_event)

        assert normalized is not None
        assert normalized.material_original is not None, "material_original should be extracted"
        assert normalized.material_new is not None, "material_new should be extracted"
        assert normalized.location is not None, "location should be extracted"
        assert normalized.event_type == "material_change"
