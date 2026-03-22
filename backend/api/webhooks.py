"""
Webhook receivers — ACC RFI creation events (primary) + Fireflies legacy.
"""
import hmac
import hashlib
from fastapi import APIRouter, BackgroundTasks, Request
from models.schemas import FirefliesWebhook, ACCWebhook
from config import settings

router = APIRouter()


# -------------------------------------------------------------------------
# ACC — primary workflow (RFI-triggered)
# -------------------------------------------------------------------------

@router.post("/acc")
async def acc_webhook(
    data: ACCWebhook,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """
    Receive ACC webhook events.
    On RFI creation, kick off the full proposal pipeline in the background.
    """
    event = data.get_event()
    print(f"📥 ACC event: {event}")

    rfi_data = data.get_rfi_data()
    project_id = data.get_project_id()

    # Handle both "rfis.rfi.created" (ACC standard) and "rfi.created" (test/legacy)
    if "rfi" in event.lower() and "created" in event.lower() and rfi_data:
        background_tasks.add_task(
            process_rfi_event,
            rfi_id=rfi_data.id,
            project_id=project_id,
            rfi_inline=rfi_data.model_dump(),
            app=request.app,
        )
        return {"status": "received", "message": f"RFI {rfi_data.id} queued for processing"}

    return {"status": "received", "event": event}


async def process_rfi_event(
    rfi_id: str,
    project_id: str | None,
    rfi_inline: dict,
    app,
):
    """
    Full RFI processing pipeline:
      1. Fetch full RFI from ACC (or use inline payload if already complete)
      2. Resolve assigned user email
      3. Haiku: extract material change from RFI description
      4. Sonnet: generate comprehensive proposal
      5. Score confidence
      6. Save to DB
      7. Broadcast to dashboard via WebSocket
    """
    from services.normalization import NormalizationService
    from services.proposal_generator import ProposalGenerator
    from services.confidence_scorer import ConfidenceScorer
    from models.database import SessionLocal, Proposal
    from integrations.acc_client import ACCClient

    print(f"\n🔄 Processing RFI: {rfi_id}")

    try:
        acc = ACCClient()

        # Step 1: Fetch full RFI details (ACC returns more fields than the webhook)
        rfi_data = await acc.get_rfi(rfi_id, project_id=project_id)
        # Merge inline payload for any fields the GET didn't return
        for k, v in rfi_inline.items():
            if v and not rfi_data.get(k):
                rfi_data[k] = v
        print(f"  RFI title: {rfi_data.get('title', '(none)')}")

        # Step 2: Resolve assignee email
        assigned_user_email = (
            rfi_data.get("assignedToEmail")
            or await acc.get_user_email(rfi_data.get("assignedTo", ""))
        )

        # Step 3: Haiku extraction
        normalizer = NormalizationService()
        extracted = await normalizer.extract_from_rfi(rfi_data)
        print(f"  Extracted: {extracted.get('material_from', '?')} → {extracted.get('material_to', '?')}")

        if not normalizer.is_rfi_actionable(extracted):
            print("  ⚠️  RFI does not describe a material change — skipping proposal")
            return

        # Step 4: Generate proposal with Sonnet
        generator = ProposalGenerator()
        proposal_record = await generator.generate_from_rfi(
            rfi_data=rfi_data,
            extracted=extracted,
            assigned_user_email=assigned_user_email,
        )
        print(f"  Proposal title: {proposal_record['title']}")

        # Step 5: Score confidence
        scorer = ConfidenceScorer()
        confidence = scorer.score(
            proposal_record.get("proposal_data", {}),
            extracted,
        )
        proposal_record["confidence"] = confidence
        print(f"  Confidence: {confidence:.0%} ({scorer.label(confidence)})")

        # Step 6: Auto-send email to RFI assignee
        email_sent = False
        email_sent_at = None
        if assigned_user_email:
            try:
                from integrations.gmail_client import GmailClient, build_proposal_email_html
                from datetime import datetime as dt
                dashboard_url = "http://localhost:5173"
                proposal_dict = {
                    "title": proposal_record["title"],
                    "summary": proposal_record.get("summary"),
                    "cost": proposal_record.get("cost", 0),
                    "confidence": confidence,
                    "proposal_data": proposal_record.get("proposal_data", {}),
                }
                gmail = GmailClient()
                await gmail.send_email(
                    to=assigned_user_email,
                    subject=f"Material Change Proposal: {proposal_record['title']}",
                    body_html=build_proposal_email_html(proposal_dict, dashboard_url),
                    body_text=(
                        f"{proposal_record['title']}\n\n"
                        f"{proposal_record.get('summary', '')}\n\n"
                        f"Cost impact: €{proposal_record.get('cost', 0):,.0f}\n"
                        f"Confidence: {round(confidence * 100)}%\n\n"
                        f"Review & act: {dashboard_url}"
                    ),
                )
                email_sent = True
                email_sent_at = dt.utcnow()
                print(f"  📧 Auto-email sent to {assigned_user_email}")
            except Exception as email_err:
                print(f"  ⚠️  Auto-email failed: {email_err}")

        # Step 7: Save to DB
        db = SessionLocal()
        try:
            record = Proposal(
                id=proposal_record["id"],
                title=proposal_record["title"],
                summary=proposal_record.get("summary"),
                status="pending",
                confidence=confidence,
                cost=proposal_record.get("cost", 0),
                actions=proposal_record.get("actions", []),
                extracted=extracted,
                proposal_data=proposal_record.get("proposal_data", {}),
                source_rfi_id=proposal_record.get("source_rfi_id"),
                acc_project_id=proposal_record.get("acc_project_id"),
                assigned_user_email=assigned_user_email,
                email_sent=email_sent,
                email_sent_at=email_sent_at,
            )
            db.add(record)
            db.commit()
            print(f"  Saved proposal {proposal_record['id'][:8]}…")
        finally:
            db.close()

        # Step 8: Broadcast to dashboard
        if hasattr(app.state, "ws_manager"):
            await app.state.ws_manager.broadcast({
                "type": "new_proposal",
                "proposal": {
                    "id": proposal_record["id"],
                    "title": proposal_record["title"],
                    "confidence": confidence,
                    "cost": proposal_record.get("cost", 0),
                    "status": "pending",
                    "source_rfi_id": proposal_record.get("source_rfi_id"),
                    "email_sent": email_sent,
                    "assigned_user_email": assigned_user_email,
                },
            })
            print("  WebSocket notification sent")

        print(f"\n🎉 RFI pipeline complete — proposal ready for review")

    except Exception as e:
        print(f"❌ RFI pipeline error: {e}")
        import traceback
        traceback.print_exc()


# -------------------------------------------------------------------------
# Fireflies — legacy transcript workflow
# -------------------------------------------------------------------------

@router.post("/fireflies")
async def fireflies_webhook(
    data: FirefliesWebhook,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Receive Fireflies transcript webhook and queue processing."""
    background_tasks.add_task(
        process_transcript,
        data.transcript,
        data.title,
        data.participants,
        request.app,
    )
    return {"status": "received", "message": "Transcript queued for processing"}


async def process_transcript(transcript: str, title: str, participants: list, app):
    """Legacy pipeline: transcript → extract → propose → score → notify."""
    from services.normalization import NormalizationService
    from services.proposal_generator import ProposalGenerator
    from services.confidence_scorer import ConfidenceScorer
    from models.database import SessionLocal, Proposal

    print(f"\n🔄 Processing transcript: '{title}'")
    try:
        normalizer = NormalizationService()
        extracted = await normalizer.extract(transcript)
        print(f"  Extracted: {extracted.get('material_from', '?')} → {extracted.get('material_to', '?')}")

        if not normalizer.is_actionable(extracted):
            print("  ⚠️  Transcript not actionable, skipping")
            return

        generator = ProposalGenerator()
        proposal_record = await generator.generate(extracted, meeting_title=title)
        print(f"  Proposal: {proposal_record['title']}")

        scorer = ConfidenceScorer()
        confidence = scorer.score(proposal_record.get("proposal_data", {}), extracted)
        proposal_record["confidence"] = confidence
        print(f"  Confidence: {confidence:.0%} ({scorer.label(confidence)})")

        db = SessionLocal()
        try:
            record = Proposal(
                id=proposal_record["id"],
                title=proposal_record["title"],
                summary=proposal_record.get("summary"),
                status="pending",
                confidence=confidence,
                cost=proposal_record.get("cost", 0),
                actions=proposal_record.get("actions", []),
                extracted=extracted,
                proposal_data=proposal_record.get("proposal_data", {}),
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        if hasattr(app.state, "ws_manager"):
            await app.state.ws_manager.broadcast({
                "type": "new_proposal",
                "proposal": {
                    "id": proposal_record["id"],
                    "title": proposal_record["title"],
                    "confidence": confidence,
                    "cost": proposal_record.get("cost", 0),
                    "status": "pending",
                },
            })

        print(f"\n🎉 Transcript pipeline complete!")

    except Exception as e:
        print(f"❌ Transcript pipeline error: {e}")
        import traceback
        traceback.print_exc()
