import importlib.util
import os
from pathlib import Path
from typing import Any


DEFAULT_REPO_PATH = "fireflies-raycast-main"
DEFAULT_MAX_CHARS = 8000


class FirefliesIntegrationError(RuntimeError):
    pass


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_fireflies_api_class(repo_path: str):
    module_path = Path(repo_path) / "fireflies_api.py"
    if not module_path.is_file():
        raise FirefliesIntegrationError(
            f"Fireflies repo not found at '{module_path}'. "
            "Set GIGAI_FIREFLIES_REPO_PATH to your fireflies-raycast repo."
        )

    spec = importlib.util.spec_from_file_location("gigai_fireflies_api", module_path)
    if spec is None or spec.loader is None:
        raise FirefliesIntegrationError(f"Failed to load Fireflies API module from '{module_path}'.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, "FirefliesAPI", None)
    if cls is None:
        raise FirefliesIntegrationError("FirefliesAPI class not found in fireflies_api.py.")
    return cls


def _render_sentence_text(transcript: dict[str, Any]) -> str:
    sentences = transcript.get("sentences")
    if not isinstance(sentences, list) or not sentences:
        return ""

    parts: list[str] = []
    for sentence in sentences:
        if not isinstance(sentence, dict):
            continue
        text = (sentence.get("text") or sentence.get("raw_text") or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def _int_env(name: str, default_value: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default_value
    try:
        value = int(raw)
    except ValueError:
        return default_value
    return value if value > 0 else default_value


def resolve_fireflies_transcript(payload: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    if not _is_truthy(os.getenv("GIGAI_FIREFLIES_ENABLED")):
        return None, {}

    transcript_id = str(
        payload.get("fireflies_transcript_id")
        or payload.get("transcript_id")
        or ""
    ).strip()
    use_latest = _is_truthy(payload.get("fireflies_latest"))

    # Do nothing unless caller explicitly requests Fireflies transcript sourcing.
    if not transcript_id and not use_latest:
        return None, {}

    repo_path = os.getenv("GIGAI_FIREFLIES_REPO_PATH", DEFAULT_REPO_PATH).strip() or DEFAULT_REPO_PATH
    api_key = (
        str(payload.get("fireflies_api_key") or "").strip()
        or os.getenv("FIREFLIES_API_KEY", "").strip()
    )
    if not api_key:
        raise FirefliesIntegrationError("FIREFLIES_API_KEY is required for Fireflies transcript retrieval.")

    try:
        fireflies_api_class = _load_fireflies_api_class(repo_path)
    except ModuleNotFoundError as ex:
        raise FirefliesIntegrationError(
            "Missing Fireflies dependencies. Install requirements from fireflies-raycast-main/requirements.txt."
        ) from ex

    client = fireflies_api_class(api_key=api_key)
    transcript_obj: dict[str, Any] | None = None
    if transcript_id:
        transcript_obj = client.get_transcript_by_id(transcript_id)
    else:
        recent = client.get_recent_transcripts(limit=1)
        if isinstance(recent, list) and recent:
            first = recent[0]
            transcript_obj = first if isinstance(first, dict) else None

    if not transcript_obj:
        raise FirefliesIntegrationError("No Fireflies transcript found for the given request.")

    rendered = _render_sentence_text(transcript_obj)
    if not rendered:
        # Fall back to the repo formatter when sentence text is missing.
        rendered = str(client.format_transcript(transcript_obj) or "").strip()
    if not rendered:
        raise FirefliesIntegrationError("Fireflies transcript was empty.")

    max_chars = _int_env("GIGAI_FIREFLIES_MAX_CHARS", DEFAULT_MAX_CHARS)
    if len(rendered) > max_chars:
        rendered = rendered[:max_chars].rstrip() + "..."

    metadata = {
        "fireflies_transcript_id": str(transcript_obj.get("id") or "").strip(),
        "fireflies_transcript_title": str(transcript_obj.get("title") or "").strip(),
        "fireflies_transcript_url": str(transcript_obj.get("transcript_url") or "").strip(),
    }
    return rendered, metadata

