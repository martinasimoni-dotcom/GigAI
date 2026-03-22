"""
Proposals API — CRUD + three action buttons + approve/reject + manual RFI trigger.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models.database import get_db, Proposal, Decision
from models.schemas import ProposalOut, RejectRequest
from integrations.acc_client import ACCClient
from integrations.gmail_client import GmailClient, build_proposal_email_html

router = APIRouter()


# -------------------------------------------------------------------------
# Manual RFI trigger — for demo use when webhooks / polling aren't available
# -------------------------------------------------------------------------

class ProcessRfiRequest(BaseModel):
    rfi_id: str


@router.post("/process-rfi")
async def process_rfi_manually(
    body: ProcessRfiRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Manually trigger the full proposal pipeline for a single ACC RFI.

    1. Fetches the RFI from ACC by ID (works with 2-legged token)
    2. Runs the same pipeline as the webhook handler
    3. Returns immediately — the proposal appears in the dashboard via WebSocket

    Body: { "rfi_id": "<ACC RFI ID>" }
    """
    rfi_id = body.rfi_id.strip()
    if not rfi_id:
        raise HTTPException(status_code=422, detail="rfi_id is required")

    from config import settings
    project_id = settings.ACC_PROJECT_ID or ""

    acc = ACCClient()
    try:
        rfi_data = await acc.get_rfi(rfi_id, project_id=project_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not rfi_data or not rfi_data.get("id"):
        raise HTTPException(
            status_code=404,
            detail=f"RFI '{rfi_id}' not found in ACC project '{project_id}'. "
                   "Check the RFI ID and ensure it belongs to the configured project.",
        )

    from api.webhooks import process_rfi_event
    import asyncio
    # Run pipeline directly (not as background task) so all output is visible in terminal
    asyncio.create_task(process_rfi_event(
        rfi_id=rfi_data.get("id") or rfi_id,
        project_id=project_id,
        rfi_inline=rfi_data,
        app=request.app,
    ))

    return {
        "status": "queued",
        "rfi_id": rfi_id,
        "title": rfi_data.get("title") or "(fetching…)",
        "message": "Pipeline started — proposal will appear in the dashboard shortly.",
    }


@router.get("/proposals", response_model=list[ProposalOut])
def get_proposals(status: str = "pending", db: Session = Depends(get_db)):
    """List proposals filtered by status."""
    query = db.query(Proposal)
    if status != "all":
        query = query.filter(Proposal.status == status)
    return query.order_by(Proposal.created_at.desc()).all()


@router.get("/proposals/{id}", response_model=ProposalOut)
def get_proposal(id: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


# -------------------------------------------------------------------------
# Individual action buttons
# -------------------------------------------------------------------------

@router.post("/proposals/{id}/create-rfi")
async def create_rfi_in_acc(id: str, db: Session = Depends(get_db)):
    """
    Button: "Create RFI in ACC"
    Creates a new RFI in ACC with the proposal details, linked to the source RFI.
    """
    proposal = _get_pending_proposal(id, db)

    proposal_data = proposal.proposal_data or {}
    cost_analysis = proposal_data.get("cost_analysis", {}) or {}
    material_change = proposal_data.get("material_change", {}) or {}

    description = _build_rfi_description(proposal, proposal_data, cost_analysis, material_change)

    acc = ACCClient()
    result = await acc.create_rfi(
        title=f"Material Change Proposal: {proposal.title}",
        description=description,
        project_id=proposal.acc_project_id,
        linked_rfi_id=proposal.source_rfi_id,
    )
    print(f"✅ Created RFI in ACC: {result.get('id')}")

    _record_decision(db, id, "rfi_created", f"ACC RFI created: {result.get('id')}")

    return {"status": "created", "rfi_id": result.get("id"), "title": result.get("title")}


@router.post("/proposals/{id}/send-email")
async def send_proposal_email(id: str, db: Session = Depends(get_db)):
    """
    Button: "Resend Email"
    Re-sends the proposal email to the RFI assignee (email was auto-sent on creation).
    """
    proposal = _get_pending_proposal(id, db)

    to_email = proposal.assigned_user_email
    if not to_email:
        raise HTTPException(
            status_code=422,
            detail="No assignee email found for this proposal. Check ACC RFI assignee.",
        )

    dashboard_url = "http://localhost:5173"  # configurable via env later
    subject = f"Material Change Proposal: {proposal.title}"

    proposal_dict = {
        "title": proposal.title,
        "summary": proposal.summary,
        "cost": proposal.cost,
        "confidence": proposal.confidence,
        "proposal_data": proposal.proposal_data,
    }
    body_html = build_proposal_email_html(proposal_dict, dashboard_url)
    body_text = (
        f"{proposal.title}\n\n"
        f"{proposal.summary or ''}\n\n"
        f"Cost impact: €{proposal.cost or 0:,.0f}\n"
        f"Confidence: {round((proposal.confidence or 0) * 100)}%\n\n"
        f"View in dashboard: {dashboard_url}"
    )

    gmail = GmailClient()
    result = await gmail.send_email(
        to=to_email,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
    )
    print(f"✅ Email sent to {to_email}")

    from datetime import datetime
    proposal.email_sent = True
    proposal.email_sent_at = datetime.utcnow()
    _record_decision(db, id, "email_sent", f"Email sent to {to_email}")
    db.commit()

    return {"status": "sent", "to": to_email, "subject": subject}


# -------------------------------------------------------------------------
# Accept / Reject
# -------------------------------------------------------------------------

@router.post("/proposals/{id}/approve")
async def approve_proposal(id: str, db: Session = Depends(get_db)):
    """
    Button: "Accept"
    1. Creates RFI in ACC with proposal details
    2. Updates original RFI status to 'answered'
    3. Sends email notification to assignee
    4. Records decision in DB
    """
    proposal = _get_pending_proposal(id, db)

    executed = []
    errors = []

    proposal_data = proposal.proposal_data or {}
    cost_analysis = proposal_data.get("cost_analysis", {}) or {}
    material_change = proposal_data.get("material_change", {}) or {}

    acc = ACCClient()

    # 1. Create proposal RFI in ACC
    try:
        description = _build_rfi_description(proposal, proposal_data, cost_analysis, material_change)
        rfi_result = await acc.create_rfi(
            title=f"Material Change Proposal: {proposal.title}",
            description=description,
            project_id=proposal.acc_project_id,
            linked_rfi_id=proposal.source_rfi_id,
        )
        executed.append({"type": "acc_rfi", "id": rfi_result.get("id")})
        print(f"  ✅ Proposal RFI created: {rfi_result.get('id')}")
    except Exception as e:
        errors.append({"type": "acc_rfi", "error": str(e)})
        print(f"  ⚠️  Create RFI failed: {e}")

    # 2. Update original RFI status
    if proposal.source_rfi_id:
        try:
            await acc.update_rfi(
                rfi_id=proposal.source_rfi_id,
                status="answered",
                comment=f"APPROVED — {proposal.title}. Confidence: {round((proposal.confidence or 0) * 100)}%",
                project_id=proposal.acc_project_id,
            )
            executed.append({"type": "acc_rfi_update", "id": proposal.source_rfi_id})
            print(f"  ✅ Source RFI updated: {proposal.source_rfi_id}")
        except Exception as e:
            errors.append({"type": "acc_rfi_update", "error": str(e)})
            print(f"  ⚠️  Update source RFI failed: {e}")

    # 3. Send email
    if proposal.assigned_user_email:
        try:
            dashboard_url = "http://localhost:5173"
            proposal_dict = {
                "title": proposal.title,
                "summary": proposal.summary,
                "cost": proposal.cost,
                "confidence": proposal.confidence,
                "proposal_data": proposal.proposal_data,
            }
            gmail = GmailClient()
            await gmail.send_email(
                to=proposal.assigned_user_email,
                subject=f"✅ APPROVED: {proposal.title}",
                body_html=build_proposal_email_html(proposal_dict, dashboard_url),
                body_text=f"Approved: {proposal.title}\n\nView in dashboard: {dashboard_url}",
            )
            executed.append({"type": "email", "to": proposal.assigned_user_email})
            print(f"  ✅ Approval email sent to {proposal.assigned_user_email}")
        except Exception as e:
            errors.append({"type": "email", "error": str(e)})
            print(f"  ⚠️  Email failed: {e}")

    # 4. Mark proposal approved + record decision
    proposal.status = "approved"
    decision = Decision(
        id=str(uuid.uuid4()),
        proposal_id=id,
        decision="approved",
        decided_by="user",
    )
    db.add(decision)
    db.commit()

    return {
        "status": "approved",
        "actions_executed": len(executed),
        "actions": executed,
        "errors": errors,
    }


@router.post("/proposals/{id}/reject")
async def reject_proposal(id: str, body: RejectRequest = None, db: Session = Depends(get_db)):
    """
    Button: "Reject"
    1. Updates original RFI in ACC with rejection reason
    2. Sends rejection email to assignee
    3. Records decision in DB
    """
    proposal = _get_pending_proposal(id, db)

    reason = (body.reason if body else "") or "Proposal rejected by coordinator."
    errors = []
    executed = []

    acc = ACCClient()

    # 1. Update original RFI
    if proposal.source_rfi_id:
        try:
            await acc.update_rfi(
                rfi_id=proposal.source_rfi_id,
                status="closed",
                comment=f"REJECTED — {reason}",
                project_id=proposal.acc_project_id,
            )
            executed.append({"type": "acc_rfi_update", "id": proposal.source_rfi_id})
            print(f"  ✅ Source RFI closed: {proposal.source_rfi_id}")
        except Exception as e:
            errors.append({"type": "acc_rfi_update", "error": str(e)})
            print(f"  ⚠️  Update source RFI failed: {e}")

    # 2. Send rejection email
    if proposal.assigned_user_email:
        try:
            gmail = GmailClient()
            await gmail.send_email(
                to=proposal.assigned_user_email,
                subject=f"❌ Rejected: {proposal.title}",
                body_html=f"<p><b>Rejected:</b> {proposal.title}</p><p>Reason: {reason}</p>",
                body_text=f"Rejected: {proposal.title}\n\nReason: {reason}",
            )
            executed.append({"type": "email", "to": proposal.assigned_user_email})
            print(f"  ✅ Rejection email sent to {proposal.assigned_user_email}")
        except Exception as e:
            errors.append({"type": "email", "error": str(e)})
            print(f"  ⚠️  Email failed: {e}")

    # 3. Mark rejected + record decision
    proposal.status = "rejected"
    decision = Decision(
        id=str(uuid.uuid4()),
        proposal_id=id,
        decision="rejected",
        reason=reason,
        decided_by="user",
    )
    db.add(decision)
    db.commit()

    return {"status": "rejected", "actions": executed, "errors": errors}


# -------------------------------------------------------------------------
# Stats + decisions
# -------------------------------------------------------------------------

@router.get("/decisions")
def get_decisions(db: Session = Depends(get_db)):
    return db.query(Decision).order_by(Decision.decided_at.desc()).limit(50).all()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Proposal).count()
    pending = db.query(Proposal).filter(Proposal.status == "pending").count()
    approved = db.query(Proposal).filter(Proposal.status == "approved").count()
    rejected = db.query(Proposal).filter(Proposal.status == "rejected").count()
    return {"total": total, "pending": pending, "approved": approved, "rejected": rejected}


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _get_pending_proposal(id: str, db: Session) -> Proposal:
    proposal = db.query(Proposal).filter(Proposal.id == id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail=f"Proposal is already {proposal.status}")
    return proposal


def _record_decision(db: Session, proposal_id: str, decision: str, reason: str = ""):
    """Append an audit record without changing proposal status."""
    record = Decision(
        id=str(uuid.uuid4()),
        proposal_id=proposal_id,
        decision=decision,
        reason=reason,
        decided_by="user",
    )
    db.add(record)
    db.commit()


def _build_rfi_description(
    proposal,
    proposal_data: dict,
    cost_analysis: dict,
    material_change: dict,
) -> str:
    lines = [
        f"## Material Change Proposal\n",
        f"**{proposal.title}**\n",
        f"{proposal.summary or ''}\n",
    ]

    if material_change:
        lines += [
            "\n### Material Change",
            f"- From: {material_change.get('from', 'N/A')}",
            f"- To: {material_change.get('to', 'N/A')}",
            f"- Quantity: {material_change.get('quantity', 'N/A')} {material_change.get('unit', '')}",
            f"- Affected areas: {material_change.get('affected_areas', 'N/A')}",
        ]

    if cost_analysis:
        delta = cost_analysis.get("total_delta_eur") or cost_analysis.get("total_eur", 0)
        lines += [
            "\n### Cost Impact",
            f"- Old unit cost: €{cost_analysis.get('old_unit_cost_eur', 'N/A'):,}",
            f"- New unit cost: €{cost_analysis.get('new_unit_cost_eur', 'N/A'):,}",
            f"- Total cost delta: €{abs(delta):,.0f}" if isinstance(delta, (int, float)) else f"- Total cost delta: {delta}",
        ]
        breakdown = cost_analysis.get("breakdown", []) or []
        if breakdown:
            lines.append("\nBreakdown:")
            for item in breakdown:
                lines.append(f"  • {item.get('item', '')}: €{item.get('cost_eur', 0):,}")

    justification = proposal_data.get("justification")
    if justification:
        lines += ["\n### Justification", justification]

    risks = proposal_data.get("risks", []) or []
    if risks:
        lines.append("\n### Risks")
        for r in risks:
            lines.append(f"- {r}")

    confidence = round((proposal.confidence or 0) * 100)
    lines += [
        f"\n### AI Confidence Score: {confidence}%",
        f"Recommendation: {proposal_data.get('recommendation', 'review').upper()}",
    ]

    if proposal.source_rfi_id:
        lines.append(f"\n_Linked to source RFI: {proposal.source_rfi_id}_")

    return "\n".join(lines)
