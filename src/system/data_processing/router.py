"""
Router module — PROC-04, PROC-05.

route_event(event: NormalizedEvent) -> RoutedEvent

Calls Haiku with the routing prompt (config/prompts/routing.txt) to classify
the event into one of: material_change, schedule_update, rfi_request, other.
Loads the matching YAML config from config/event_types/.
Publishes the NormalizedEvent to the normalized-events Pub/Sub topic.
Falls back to "other" if classification is unrecognised or YAML loading fails.
"""
import json
import logging
from pathlib import Path

import yaml
from google.cloud import pubsub_v1
from pydantic import BaseModel, ConfigDict, ValidationError

from config.settings import settings
from src.shared.llm.claude import call_haiku
from src.shared.models.config import EventTypeConfig
from src.shared.models.events import NormalizedEvent

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "prompts" / "routing.txt"
)
_CONFIG_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "event_types"
)

_VALID_EVENT_TYPES = {"material_change", "schedule_update", "rfi_request", "other"}

_ROUTING_SCHEMA = {
    "type": "object",
    "properties": {
        "event_type": {"type": "string"},
        "confidence": {"type": "integer"},
    },
    "required": ["event_type", "confidence"],
}

_SYSTEM = (
    "You are a construction project event classifier. "
    "Respond ONLY with valid JSON with keys 'event_type' and 'confidence'."
)


class RoutedEvent(BaseModel):
    """Output of the routing step."""
    model_config = ConfigDict(str_strip_whitespace=True)

    event: NormalizedEvent
    event_type: str
    config: EventTypeConfig
    config_path: str


def _load_routing_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _publish_normalized_event(event: NormalizedEvent) -> str:
    """Publish NormalizedEvent to the normalized-events Pub/Sub topic."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        settings.google_cloud_project,
        settings.pubsub_topic_normalized_events,
    )
    payload = event.model_dump(mode="json")
    data = json.dumps(payload).encode("utf-8")
    future = publisher.publish(topic_path, data, event_type=event.event_type)
    message_id: str = future.result()
    logger.info({
        "event": "normalized_event_published",
        "event_id": event.event_id,
        "event_type": event.event_type,
        "message_id": message_id,
    })
    return message_id


def route_event(event: NormalizedEvent, config_dir: Path | None = None) -> RoutedEvent:
    """
    Classify a NormalizedEvent and load its processing config.

    Calls Haiku with the routing prompt to determine event_type.
    Loads the matching YAML from config/event_types/{event_type}.yaml.
    Publishes the NormalizedEvent to the normalized-events Pub/Sub topic.
    Falls back to event_type="other" if classification is unrecognised or YAML fails.

    Args:
        event: The normalized event to route.
        config_dir: Optional override for config directory (used in tests).

    Returns:
        RoutedEvent with event, event_type, config, and config_path.
    """
    effective_config_dir = Path(config_dir) if config_dir else _CONFIG_DIR

    base_prompt = _load_routing_prompt()
    event_json = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
    full_prompt = f"{base_prompt}\n\n{event_json}"

    event_type = "other"
    try:
        raw_json = call_haiku(
            prompt=full_prompt,
            system=_SYSTEM,
            output_schema=_ROUTING_SCHEMA,
        )
        data = json.loads(raw_json)
        classified = data.get("event_type", "other")
        if classified in _VALID_EVENT_TYPES:
            event_type = classified
        else:
            logger.warning({
                "event": "unknown_event_type",
                "classified": classified,
                "fallback": "other",
            })
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning({
            "event": "routing_failed",
            "error": str(exc),
            "fallback": "other",
        })

    # Load config — falls back to other on failure
    config_path = effective_config_dir / f"{event_type}.yaml"
    try:
        with open(config_path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        config = EventTypeConfig(**yaml_data)
    except (FileNotFoundError, ValidationError, TypeError) as exc:
        logger.warning({
            "event": "config_load_failed",
            "event_type": event_type,
            "error": str(exc),
            "fallback": "other",
        })
        event_type = "other"
        config_path = effective_config_dir / "other.yaml"
        with open(config_path, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
        config = EventTypeConfig(**yaml_data)

    # Publish to normalized-events topic
    _publish_normalized_event(event)

    return RoutedEvent(
        event=event,
        event_type=event_type,
        config=config,
        config_path=str(config_path),
    )
