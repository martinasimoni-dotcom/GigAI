"""
Seed data for RFI queue — pre-populated RFIs at various lifecycle stages.
"""
import logging
from datetime import datetime, timedelta, timezone

from src.rfi.models import RFI, RFIResponse
from src.rfi.store import rfi_store
from src.rfi.detector import scan_inbox_for_rfis

logger = logging.getLogger(__name__)


def _ago(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def seed_rfis() -> int:
    """Seed the RFI store with auto-detected + pre-built RFIs. Returns count."""
    rfi_store.clear()

    # First: scan inbox for auto-detected RFIs
    detected = scan_inbox_for_rfis()
    logger.info("Auto-detected %d RFIs from inbox", detected)

    # Then: add some pre-built RFIs at various lifecycle stages for demo
    _add_lifecycle_rfis()

    total = rfi_store.count
    logger.info("RFI store seeded with %d total items", total)
    return total


def _add_lifecycle_rfis():
    """Add RFIs at various lifecycle stages to demo the full workflow."""
    # A drafted RFI (response ready for PM review)
    rfi_store.add(RFI(
        rfi_id="RFI-DEMO-001",
        project_id="PRJ-001", project_name="Harbor View Tower",
        title="Structural load capacity for wood window frames on 3rd floor",
        question="The structural engineer needs to confirm that the 3rd floor wall system can support the additional weight of wood window frames (approx. 15% heavier than aluminum). The current structural calculations were done for aluminum frames. Do we need updated calcs?",
        category="structural",
        status="drafted",
        priority="high",
        assignee="Lisa Wong",
        requester="James Park",
        requester_email="j.park@parkstudioarch.com",
        response=RFIResponse(
            draft_text="Based on the structural analysis performed for the Harbor View Tower project, the 3rd floor wall system was designed with a safety factor of 1.5 for the original aluminum window frames (weight: 12.5 kg/unit). Wood frames at approximately 14.4 kg/unit represent a 15% weight increase.\n\nPer our review of the structural drawings (S-301, S-302) and ACI 318-19 Section 6.6, the existing wall system has adequate capacity to support the additional load. The dead load increase of 22.8 kg total (1.9 kg × 12 units) is well within the designed margins.\n\nHowever, we recommend:\n1. Updated structural calculations documenting the load change (for permit file)\n2. Verification of the lintel spans at W-301 through W-312\n3. Confirmation that the wood frame anchoring system meets ASTM E2768 requirements\n\nNo structural remediation is required.",
            knowledge_sources=["Structural drawings S-301, S-302", "ACI 318-19 Section 6.6", "ASTM E2768 fire resistance"],
            confidence=0.85,
            drafted_at=_ago(6),
        ),
        created_at=_ago(24),
    ))

    # A sent RFI (waiting for external response)
    rfi_store.add(RFI(
        rfi_id="RFI-DEMO-002",
        project_id="PRJ-001", project_name="Harbor View Tower",
        title="FSC certification requirements for wood window frame material",
        question="Premium Wood Co. offers both FSC Mix and FSC 100% certified wood. The spec calls for 'FSC certified' without specifying the chain-of-custody level. Which certification level is acceptable?",
        category="materials",
        status="sent",
        priority="medium",
        assignee="Mike Torres",
        requester="Jane Miller",
        requester_email="j.miller@premiumwoodco.com",
        response=RFIResponse(
            draft_text="Per project specification Section 061000, the LEED Gold certification requires FSC-certified wood products contributing to MR Credit: Building Product Disclosure. Both FSC Mix (minimum 70% FSC-certified content) and FSC 100% satisfy LEED v4.1 requirements.\n\nRecommendation: Accept FSC Mix certification, which provides cost savings of approximately 12% while meeting all project sustainability requirements. Ensure chain-of-custody documentation is provided with each delivery for LEED submittal package.",
            knowledge_sources=["LEED v4.1 MR Credit requirements", "Project spec Section 061000", "FSC standards"],
            confidence=0.90,
            drafted_at=_ago(48),
            edited_by_pm=True,
            pm_edits="Per project specification Section 061000 and LEED v4.1 MR Credit requirements, FSC Mix certification (minimum 70% FSC content) is acceptable. Please provide chain-of-custody documentation with each delivery. FSC 100% is preferred but not required.",
        ),
        sent_at=_ago(40),
        created_at=_ago(72),
    ))

    # A closed RFI (fully resolved)
    rfi_store.add(RFI(
        rfi_id="RFI-DEMO-003",
        project_id="PRJ-001", project_name="Harbor View Tower",
        title="Fire rating for corridor partition walls — 1-hour vs 2-hour requirement",
        question="Local code may require 2-hour fire-rated corridor walls for buildings over 4 stories. Current specs show 1-hour rating. Which is correct for Harbor View Tower (24 stories)?",
        category="fire-protection",
        status="closed",
        priority="high",
        assignee="James Park",
        requester="Fire Protection Engineer",
        response=RFIResponse(
            draft_text="Per IBC 2021 Table 602 and local amendment Section 403.2.1, buildings exceeding 4 stories require 2-hour fire-rated corridor walls in residential occupancies (Group R-2). Harbor View Tower at 24 stories is classified as High-Rise per IBC Section 403.\n\nThe current specification showing 1-hour rating is incorrect and must be updated to 2-hour fire-rated assemblies for all corridor partition walls on floors 1-24.\n\nRecommended assembly: UL Design U419 (2-hour rated, Type X gypsum on steel studs).\n\nAction required: Update architectural specs Section 092900 and fire protection drawings FP-001 through FP-024.",
            knowledge_sources=["IBC 2021 Table 602", "IBC Section 403 High-Rise", "UL Design U419"],
            confidence=0.95,
            drafted_at=_ago(120),
            edited_by_pm=True,
            pm_edits="Confirmed: 2-hour fire rating required per IBC 2021. Specs updated to UL Design U419. Drawing revisions issued as Addendum A-003.",
        ),
        sent_at=_ago(96),
        responded_at=_ago(72),
        closed_at=_ago(48),
        created_at=_ago(168),
    ))
