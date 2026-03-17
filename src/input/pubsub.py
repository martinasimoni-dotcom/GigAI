"""
Shared Pub/Sub publisher helper for all input ingestion paths.
Centralizes client construction, topic path formatting, and RawEvent serialization.
"""
import json
import logging

from google.cloud import pubsub_v1

from config.settings import settings
from src.shared.models.events import RawEvent

logger = logging.getLogger(__name__)

_publisher: pubsub_v1.PublisherClient | None = None
_topic_path: str | None = None


def _get_publisher() -> tuple[pubsub_v1.PublisherClient, str]:
    """Lazy init: construct PublisherClient and topic path on first call."""
    global _publisher, _topic_path
    if _publisher is None:
        if not settings.google_cloud_project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is not set in .env. "
                "This is required for Pub/Sub event publishing."
            )
        _publisher = pubsub_v1.PublisherClient()
        _topic_path = _publisher.topic_path(
            settings.google_cloud_project,
            settings.pubsub_topic_raw_events,
        )
    return _publisher, _topic_path


def publish_event(raw_event: RawEvent) -> str:
    """
    Publish a RawEvent to the raw-events Pub/Sub topic.

    Serializes the RawEvent to JSON bytes using model_dump(mode="json") to ensure
    datetime fields are converted to ISO strings (not Python datetime objects, which
    are not JSON-serializable).

    Passes source as a Pub/Sub message attribute for subscription-side filtering.

    Calls future.result() synchronously to surface any publish errors immediately
    (without this, failures are silently dropped as the publish is async internally).

    Returns:
        message_id: str — the Pub/Sub message ID confirming delivery to the topic.

    Raises:
        google.api_core.exceptions.GoogleAPICallError: if publish fails after retries.
    """
    publisher, topic_path = _get_publisher()
    # model_dump(mode="json") converts datetime -> ISO string; prevents TypeError in json.dumps
    payload = raw_event.model_dump(mode="json")
    data: bytes = json.dumps(payload).encode("utf-8")
    future = publisher.publish(topic_path, data, source=raw_event.source)
    message_id: str = future.result()  # blocks until confirmed; raises on failure
    logger.info({"event": "pubsub_published", "source": raw_event.source, "message_id": message_id})
    return message_id
