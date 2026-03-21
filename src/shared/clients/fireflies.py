"""
Fireflies GraphQL API client.

Polls the Fireflies API for recent meeting transcripts using the API key.
No webhook or public URL needed — this is a pull-based approach.
"""
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

FIREFLIES_API_URL = "https://api.fireflies.ai/graphql"

_TRANSCRIPTS_QUERY = """
query GetRecentTranscripts {
  transcripts(limit: 10) {
    id
    title
    date
    duration
    participants
    sentences {
      text
      speaker_name
    }
    summary {
      action_items
      overview
      keywords
    }
  }
}
"""


def get_recent_transcripts(api_key: str) -> list[dict]:
    """
    Fetch the 10 most recent transcripts from Fireflies.

    Args:
        api_key: Fireflies API key (from settings.fireflies_api_key).

    Returns:
        List of transcript dicts. Empty list on error.
    """
    payload = json.dumps({"query": _TRANSCRIPTS_QUERY}).encode("utf-8")

    req = urllib.request.Request(
        FIREFLIES_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Fireflies API request failed: %s", exc)
        return []

    if "errors" in body:
        logger.warning("Fireflies API returned errors: %s", body["errors"])
        return []

    return body.get("data", {}).get("transcripts", []) or []
