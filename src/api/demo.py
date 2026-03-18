"""
POST /demo/trigger

Fires the exact scenario from the GigAI presentation (slide 31):
  Material Change Coordination Workflow
  Window material substitution > 3rd floor windows | Aluminum -> Wood | 12 units

Injects a pre-built Fireflies transcript directly into the synchronous pipeline.
No external meeting, no Pub/Sub, no GCP needed — just runs and pushes the proposal
to the dashboard via SSE.
"""
import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src.shared.models.events import RawEvent

router = APIRouter(prefix="/demo", tags=["demo"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# The exact transcript from the presentation scenario
# ---------------------------------------------------------------------------

_DEMO_TRANSCRIPT = """
Meeting: Barcelona Tower Project — Weekly Design Review
Date: 2026-03-18
Attendees: Sarah Chen (Project Manager), James Park (Lead Architect),
           Lisa Wong (Structural Engineer), Carlos Rivera (Site Superintendent)

Transcript:

Sarah Chen: Okay let's start. James, you wanted to flag something about the 3rd floor windows?

James Park: Yes. We've had a supplier issue — our aluminum frame supplier, Euroframe,
has a 14-week backlog. They can't deliver the 12 units we need for the 3rd floor
on schedule. I'm proposing we substitute aluminum frames with wood frames for
those 12 window units.

Lisa Wong: Wood frames on the 3rd floor — I'd need to check the structural weight
implications. Wood is heavier than aluminum. I'll run the numbers.

Sarah Chen: How much is the cost difference?

James Park: Wood frames from Premium Wood Co. — I've spoken to Jane Miller there —
are about $850 per unit. So roughly $10,200 total for the 12 units. That's about
$2,400 more than the aluminum option.

Carlos Rivera: The 3rd floor crew is ready to install in 3 weeks. If we switch
to wood we need to know now so we can update the drawings.

Sarah Chen: Okay. Action items: James — update the drawing A-301 to reflect wood
frames. Lisa — send me the structural weight assessment by end of this week.
I'll contact Premium Wood Co. and get a formal quote. We need FSC certified wood,
make sure Jane Miller knows that. Carlos — I'll create a task in ACC for the
installation crew to hold until we confirm.

James Park: Should I open an RFI with the specification update?

Sarah Chen: Yes, open an RFI in ACC. I'll review it today.

Meeting ended 11:42 AM.
"""

_DEMO_PAYLOAD = {
    "id": "ff-demo-transcript-001",
    "meetingId": "barcelona-tower-weekly-2026-03-18",
    "meeting": {
        "title": "Barcelona Tower Project — Weekly Design Review",
        "date": "2026-03-18",
        "duration": 1842,
    },
    "transcript": _DEMO_TRANSCRIPT,
    "sentences": [
        {
            "text": "Window material substitution: aluminum frames to wood frames, 3rd floor, 12 units.",
            "speaker": "James Park",
        },
        {
            "text": "Cost estimate: $10,200 total for 12 wood frame window units from Premium Wood Co.",
            "speaker": "Sarah Chen",
        },
    ],
    "summary": {
        "action_items": [
            "Update drawing A-301 to reflect wood window frames (James Park)",
            "Structural weight assessment for wood frames (Lisa Wong)",
            "Get quote from Premium Wood Co. — Jane Miller — FSC certified (Sarah Chen)",
            "Create ACC task for installation crew hold (Sarah Chen)",
            "Open RFI in ACC for specification update (James Park)",
        ]
    },
}


class TriggerRequest(BaseModel):
    """Optional overrides for the demo scenario."""
    material_original: Optional[str] = None
    material_new: Optional[str] = None
    quantity: Optional[int] = None
    location: Optional[str] = None


@router.post("/trigger")
async def trigger_demo(request: TriggerRequest = None):
    """
    Fire the presentation demo scenario through the full pipeline.

    Injects the window substitution transcript and runs:
      normalize -> route -> enrich -> policy -> signals -> proposal -> SSE push

    The proposal appears on the dashboard within ~10 seconds (LLM calls).
    Returns the full proposal_response when complete.
    """
    payload = dict(_DEMO_PAYLOAD)

    # Allow minor overrides for live demo flexibility
    if request:
        if request.material_original:
            payload["transcript"] = payload["transcript"].replace("aluminum frames", request.material_original)
        if request.material_new:
            payload["transcript"] = payload["transcript"].replace("wood frames", request.material_new)
        if request.quantity:
            payload["transcript"] = payload["transcript"].replace("12 units", f"{request.quantity} units")
        if request.location:
            payload["transcript"] = payload["transcript"].replace("3rd floor", request.location)

    raw_event = RawEvent(
        event_id=str(uuid.uuid4()),
        source="fireflies",
        raw_payload=payload,
    )

    logger.info("Demo trigger fired — event_id=%s", raw_event.event_id)

    from src.demo.pipeline import run_pipeline
    loop = asyncio.get_event_loop()
    proposal_response = await loop.run_in_executor(None, run_pipeline, raw_event)

    return {
        "status": "ok",
        "message": "Pipeline complete — proposal pushed to dashboard",
        "proposal_id": proposal_response["id"],
        "confidence_score": proposal_response["confidence_score"],
        "recommendation": proposal_response["recommendation"],
        "triggered_rules": proposal_response["triggered_rules"],
        "pipeline_ms": proposal_response["pipeline_ms"],
    }
