"""Dashboard Notifier (OUT-07): SSE push via asyncio.Queue."""
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

_queue: asyncio.Queue = asyncio.Queue(maxsize=100)


def notify_dashboard(proposal_response: dict) -> None:
    """Enqueue a proposal_response dict for SSE delivery."""
    try:
        _queue.put_nowait(proposal_response)
        logger.debug("Dashboard notification enqueued: id=%s", proposal_response.get("id"))
    except asyncio.QueueFull:
        logger.warning(
            "Dashboard SSE queue full — dropping notification id=%s",
            proposal_response.get("id"),
        )


async def get_event_stream():
    """Async generator yielding SSE-formatted strings from the queue."""
    while True:
        item = await _queue.get()
        yield f"data: {json.dumps(item)}\n\n"
