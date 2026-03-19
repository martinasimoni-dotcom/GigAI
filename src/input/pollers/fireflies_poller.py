"""
Fireflies polling connector.

Polls the Fireflies API every POLL_INTERVAL seconds for new transcripts.
Deduplicates via the processed_events table so nothing runs twice.
Runs the full pipeline for each new transcript found.
"""
import logging
import uuid

from src.shared.clients.fireflies import get_recent_transcripts
from src.shared.db.postgres import get_connection, release_connection
from src.shared.models.events import RawEvent

logger = logging.getLogger(__name__)


def _is_processed(transcript_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM processed_events WHERE source = 'fireflies' AND source_id = %s",
                (transcript_id,),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def _mark_processed(transcript_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO processed_events (source, source_id) VALUES ('fireflies', %s) ON CONFLICT DO NOTHING",
                (transcript_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def poll_once() -> int:
    """
    Poll Fireflies once, run pipeline for any new transcripts.
    Returns the number of transcripts processed.
    """
    from config.settings import settings

    if not settings.fireflies_api_key:
        logger.info("FIREFLIES_API_KEY not set — skipping Fireflies poll")
        return 0

    transcripts = get_recent_transcripts(api_key=settings.fireflies_api_key)
    if not transcripts:
        logger.debug("Fireflies poll: no transcripts returned")
        return 0

    processed = 0
    for transcript in transcripts:
        tid = transcript.get("id")
        if not tid:
            continue
        if _is_processed(tid):
            logger.debug("Fireflies transcript %s already processed — skipping", tid)
            continue

        sentences = [
            {"text": s.get("text", ""), "speaker": s.get("speaker_name", "")}
            for s in (transcript.get("sentences") or [])
        ]
        full_text = "\n".join(s["text"] for s in sentences)
        summary = transcript.get("summary") or {}

        payload = {
            "id": tid,
            "meetingId": tid,
            "meeting": {
                "title": transcript.get("title", "Untitled Meeting"),
                "date": transcript.get("date", ""),
                "duration": transcript.get("duration", 0),
            },
            "transcript": full_text,
            "sentences": sentences,
            "summary": {
                "action_items": summary.get("action_items") or [],
                "overview": summary.get("overview") or "",
            },
        }

        raw_event = RawEvent(
            event_id=str(uuid.uuid4()),
            source="fireflies",
            raw_payload=payload,
        )

        try:
            from src.demo.pipeline import run_pipeline
            run_pipeline(raw_event)
            _mark_processed(tid)
            processed += 1
            logger.info("Processed Fireflies transcript id=%s title=%s", tid, transcript.get("title"))
        except Exception as exc:
            logger.error("Pipeline failed for Fireflies transcript %s: %s", tid, exc)

    return processed
