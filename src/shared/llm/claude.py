"""
Claude LLM client wrappers.
FOUND-04

Provides call_sonnet() and call_haiku() for use throughout the pipeline.
Both support structured JSON output via output_config parameter (GA as of Nov 2025).

Model strings are locked constants:
- SONNET_MODEL = "claude-sonnet-4-20250514"  (legacy snapshot, still valid)
- HAIKU_MODEL  = "claude-haiku-4-5-20251001" (current)
"""
import logging
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Locked model identifiers — do not change without explicit user decision
SONNET_MODEL = "claude-sonnet-4-20250514"
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Lazy client — instantiated on first call so .env is loaded before key is read
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        from config.settings import settings
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def call_sonnet(
    prompt: str,
    system: str,
    output_schema: dict | None = None,
    max_tokens: int = 8192,
) -> str:
    """
    Call Claude Sonnet 4 and return the response text.

    Args:
        prompt: The user message content.
        system: The system prompt (sets Claude's role and output format).
        output_schema: Optional JSON Schema dict. When provided, uses output_config
                       for guaranteed structured JSON output (GA, no beta header needed).
        max_tokens: Maximum tokens to generate. Default 8192.

    Returns:
        Response text as a string. If output_schema was provided, this is a JSON string.
    """
    kwargs: dict[str, Any] = {
        "model": SONNET_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    if output_schema:
        kwargs["output_config"] = {
            "format": {
                "type": "json_schema",
                "schema": output_schema,
            }
        }
    response = _get_client().messages.create(**kwargs)
    return response.content[0].text


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def call_haiku(
    prompt: str,
    system: str,
    output_schema: dict | None = None,
    max_tokens: int = 4096,
) -> str:
    """
    Call Claude Haiku 4.5 and return the response text.

    Haiku is used for normalization and routing tasks — lower latency and cost
    than Sonnet, sufficient for structured extraction from clear inputs.

    Args:
        prompt: The user message content.
        system: The system prompt. For JSON extraction tasks, instruct:
                "Respond ONLY with valid JSON matching the schema below."
        output_schema: Optional JSON Schema for guaranteed structured output.
        max_tokens: Maximum tokens to generate. Default 4096.

    Returns:
        Response text as a string.
    """
    kwargs: dict[str, Any] = {
        "model": HAIKU_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    if output_schema:
        kwargs["output_config"] = {
            "format": {
                "type": "json_schema",
                "schema": output_schema,
            }
        }
    response = _get_client().messages.create(**kwargs)
    return response.content[0].text
