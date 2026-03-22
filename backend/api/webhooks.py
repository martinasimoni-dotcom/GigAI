"""
Webhook receivers -- ACC RFI creation events (primary) + Fireflies legacy.

Supported event paths:
  * dm.version.added   (data system) -- DM version added; we check whether the
    item looks like an RFI and, if so, fetch it from the ACC RFIs API.
  * rfis.rfi.created / autodesk.construction...:rfis-1.created.v1
    (ACC-native events -- used when the ACC entitlement allows them)
"""
import json
import hmac
import hashlib
import logging
from fastapi import APIRouter, BackgroundTasks, Request
from models.schemas import FirefliesWebhook, ACCWebhook
from config import settings

log = logging.getLogger("gigai")
router = APIRouter()


# -------------------------------------------------------------------------
# Helpers -- event name extraction
# -------------------------------------------------------------------------

def _extract_event(body: dict) -> str:
    """
    Pull the event name out of whatever envelope ACC/APS actually sent.

    Known locations (checked in priority order):
      1. body["payload"]["hook"]["event"]        -- DM webhooks (dm.version.added)
      2. body["payload"]["event"]                -- ACC-native envelope
      3. body["event"]                           -- flat test/legacy envelope
      4. body["eventType"]                       -- some older APS events
      5. body["type"]                            -- occasional variant
    """
    root_hook = body.get("hook") or {}
    payload   = body.get("payload") or {}
    hook      = payload.get("hook") or {}

    return (
        root_hook.get("event")
        or hook.get("event")
        or payload.get("event")
        or payload.get("eventType")
        or body.get("event")
        or body.get("eventType")
        or body.get("type")
        or ""
    )


def _extract_dm_payload(body: dict) -> dict:
    payload = body.get("payload") or {}
    merged = {**payload, **{k: v for k, v in body.items() if k != "hook"}}
    return merged


def _dm_payload_looks_like_rfi(dm_payload: dict) -> bool:
    ext          = dm_payload.get("ext") or {}
    ext_type     = (ext.get("type") or "").lower()
    display_name = (dm_payload.get("displayName") or "").lower()
    folder_urn   = (dm_payload.get("folder") or "").lower()

    return (
        "rfi" in ext_type
        or "rfi" in display_name
        or "rfis" in folder_urn
    )


# -------------------------------------------------------------------------
# ACC -- primary workflow (RFI-triggered)
# -------------------------------------------------------------------------

@router.post("/acc")
async def acc_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        body = await request.json()
    except Exception as exc:
        log.error("ACC webhook: failed to parse JSON body -- %s", exc)
        return {"status": "error", "detail": "invalid JSON"}

    log.info("ACC webhook received")
    log.info("Raw payload: %s", json.dumps(body, indent=2))

    event = _extract_event(body)
    log.info("Resolved event: %r", event)

    if not event:
        log.warning("Could not resolve event name. Root keys: %s", list(body.keys()))

    if event in ("dm.version.added", "dm.folder.created"):
        dm_payload = _extract_dm_payload(body)

        if not _dm_payload_looks_like_rfi(dm_payload):
            display = dm_payload.get("displayName", "(no name)")
            ext_type = (dm_payload.get("ext") or {}).get("type", "")
            log.info("Skipping non-RFI DM item: %r  (ext.type=%r)", display, ext_type)
            return {"status": "received", "event": event, "action": "skipped"}

        project_id   = dm_payload.get("project", "")
        display_name = dm_payload.get("displayName", "")
        resource_urn = dm_payload.get("resourceUrn", "")
        log.info("RFI item detected: %r  (project=%s)", display_name, project_id)

        background_tasks.add_task(
            process_dm_rfi_event,
            project_id=project_id,
            display_name=display_name,
            _resource_urn=resource_urn,
            app=request.app,
        )
        return {
            "status": "received",
            "event": event,
            "action": "rfi_queued",
            "item": display_name,
        }

    try:
        data = ACCWebhook.model_validate(body)
    except Exception as exc:
        log.warning("ACCWebhook schema validation failed: %s", exc)
        return {"status": "received", "event": event or "unknown"}

    rfi_data   = data.get_rfi_data()
    project_id = data.get_project_id()

    if "rfi" in event.lower() and "created" in event.lower() and rfi_data:
        log.info("ACC-native RFI created: id=%s", rfi_data.id)
        background_tasks.add_task(
            process_rfi_event,
            rfi_id=rfi_data.id,
            project_id=project_id,
            rfi_inline=rfi_data.model_dump(),
            app=request.app,
        )
        return {"status": "received", "message": f"RFI {rfi_data.id} queued for processing"}

    log.info("No handler matched event %r -- acknowledged and ignored", event)
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

    print(f"\n{'='*60}", flush=True)
    print(f"PIPELINE START -- RFI: {rfi_id}", flush=True)
    print(f"{'='*60}", flush=True)
    log.info("=" * 60)
    log.info("PIPELINE START -- RFI: %s", rfi_id)
    log.info("=" * 60)

    try:
        acc = ACCClient()

        # -- Step 1: Fetch RFI from ACC ----------------------------------------
        print("[1/8] Fetching RFI from ACC...", flush=True)
        log.info("[1/8] Fetching RFI from ACC...")
        try:
            rfi_data = await acc.get_rfi(rfi_id, project_id=project_id)
            for k, v in rfi_inline.items():
                if v and not rfi_data.get(k):
                    rfi_data[k] = v
            log.info("  OK  title       = %r", rfi_data.get('title', '(none)'))
            log.info("       description = %r", str(rfi_data.get('description', ''))[:120])
            log.info("       assignedTo  = %s", rfi_data.get('assignedTo'))
            log.info("       projectId   = %s", rfi_data.get('projectId'))
        except Exception as e:
            log.error("[1/8] FAILED: %s", e, exc_info=True)
            return

        # -- Step 2: Resolve assignee email ------------------------------------
        print("[2/8] Resolving assignee email...", flush=True)
        log.info("[2/8] Resolving assignee email...")
        log.info("  RFI keys: %s", list(rfi_data.keys()))
        try:
            # Extract user ID — check all known field variants for "ball in court"
            bic = rfi_data.get("ballInCourt") or {}
            bic_user_id = (
                (bic.get("objectId") if isinstance(bic, dict) else None)
                or rfi_data.get("ballInCourtId")
            )
            assigned_to = rfi_data.get("assignedTo") or ""
            if isinstance(assigned_to, dict):
                assigned_to = assigned_to.get("objectId") or assigned_to.get("id") or ""

            user_id = bic_user_id or assigned_to or ""
            log.info("  ballInCourt field  = %r", rfi_data.get("ballInCourt"))
            log.info("  assignedTo field   = %r", rfi_data.get("assignedTo"))
            log.info("  resolved user_id   = %r", user_id)

            assigned_user_email = (
                rfi_data.get("assignedToEmail")
                or (await acc.get_user_email(user_id) if user_id else None)
            )
            log.info("  resolved email     = %r", assigned_user_email)
        except Exception as e:
            log.warning("[2/8] Could not resolve email: %s", e)
            assigned_user_email = None

        # -- Step 3: Claude Haiku extraction ----------------------------------
        print("[3/8] Claude Haiku -- extracting material change...", flush=True)
        log.info("[3/8] Claude Haiku -- extracting material change...")
        try:
            normalizer = NormalizationService()
            extracted = await normalizer.extract_from_rfi(rfi_data)
            log.info("  OK  material_from = %r", extracted.get('material_from'))
            log.info("       material_to   = %r", extracted.get('material_to'))
            log.info("       relevant      = %s", extracted.get('relevant'))
            log.info("       location      = %r", extracted.get('location'))
            log.info("       summary       = %r", str(extracted.get('summary', ''))[:100])
            if extracted.get("error"):
                log.warning("  parse error in Haiku response: %s", extracted.get('raw', '')[:200])
        except Exception as e:
            log.error("[3/8] FAILED: %s", e, exc_info=True)
            return

        # If Haiku returned relevant=False but title implies a material change,
        # treat it as relevant and synthesize minimal fields from the title.
        title_lower = (rfi_data.get("title") or "").lower()
        change_keywords = ["change", "replace", "upgrade", "switch", "new", "install", "remove"]
        material_keywords = ["window", "door", "floor", "wall", "ceiling", "tile", "beam",
                             "pipe", "cable", "insulation", "facade", "roof", "glass", "steel",
                             "concrete", "wood", "pvc", "aluminum", "aluminium", "material"]
        title_implies_change = (
            any(kw in title_lower for kw in change_keywords)
            and any(kw in title_lower for kw in material_keywords)
        )
        if extracted.get("relevant") is False and title_implies_change:
            log.info("  NOTE: Haiku said not relevant but title implies material change -- overriding")
            extracted["relevant"] = True
            if not extracted.get("material_from"):
                extracted["material_from"] = title_lower.replace("change", "").replace("replace", "").strip() or "element"
            if not extracted.get("material_to"):
                extracted["material_to"] = f"replacement {extracted.get('material_from', 'element')}"
            if not extracted.get("summary"):
                extracted["summary"] = f"Material change: {rfi_data.get('title', '')}"

        actionable = normalizer.is_rfi_actionable(extracted)
        log.info("[3b] Actionable check: %s", actionable)
        if not actionable:
            log.warning("  STOPPING -- RFI not actionable. extracted = %s", extracted)
            return

        # -- Step 4: Claude Sonnet proposal -----------------------------------
        print("[4/8] Claude Sonnet -- generating proposal...", flush=True)
        log.info("[4/8] Claude Sonnet -- generating proposal...")
        try:
            generator = ProposalGenerator()
            proposal_record = await generator.generate_from_rfi(
                rfi_data=rfi_data,
                extracted=extracted,
                assigned_user_email=assigned_user_email,
            )
            log.info("  OK  title   = %r", proposal_record['title'])
            log.info("       summary = %r", str(proposal_record.get('summary', ''))[:100])
            log.info("       cost    = %s", proposal_record.get('cost'))
        except Exception as e:
            log.error("[4/8] FAILED: %s", e, exc_info=True)
            return

        # -- Step 5: Confidence scoring ----------------------------------------
        print("[5/8] Scoring confidence...", flush=True)
        log.info("[5/8] Scoring confidence...")
        try:
            scorer = ConfidenceScorer()
            confidence = scorer.score(proposal_record.get("proposal_data", {}), extracted)
            proposal_record["confidence"] = confidence
            log.info("  OK  confidence = %.0f%% (%s)", confidence * 100, scorer.label(confidence))
        except Exception as e:
            log.error("[5/8] FAILED: %s", e, exc_info=True)
            return

        # -- Step 6: Send email -----------------------------------------------
        print(f"[6/8] Sending email to: {assigned_user_email or 'NO EMAIL FOUND'}", flush=True)
        log.info("[6/8] Sending email...")
        email_sent = False
        email_sent_at = None
        if not assigned_user_email:
            log.info("  SKIP -- no assignee email")
        else:
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
                        f"Cost impact: EUR{proposal_record.get('cost', 0):,.0f}\n"
                        f"Confidence: {round(confidence * 100)}%\n\n"
                        f"Review & act: {dashboard_url}"
                    ),
                )
                email_sent = True
                email_sent_at = dt.utcnow()
                log.info("  OK  email sent to %s", assigned_user_email)
            except Exception as e:
                log.warning("  email failed (non-fatal): %s", e)

        # -- Step 7: Save to DB -----------------------------------------------
        print("[7/8] Saving to database...", flush=True)
        log.info("[7/8] Saving to database...")
        try:
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
                log.info("  OK  proposal %s... saved", proposal_record['id'][:8])
            finally:
                db.close()
        except Exception as e:
            log.error("[7/8] FAILED: %s", e, exc_info=True)
            return

        # -- Step 8: WebSocket broadcast --------------------------------------
        print("[8/8] Broadcasting to dashboard...", flush=True)
        log.info("[8/8] Broadcasting to dashboard...")
        try:
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
                log.info("  OK  WebSocket broadcast sent")
            else:
                log.warning("  SKIP -- no ws_manager on app.state")
        except Exception as e:
            log.warning("  WebSocket failed (non-fatal): %s", e)

        print(f"{'='*60}", flush=True)
        print("PIPELINE COMPLETE", flush=True)
        print(f"{'='*60}\n", flush=True)
        log.info("=" * 60)
        log.info("PIPELINE COMPLETE")
        log.info("=" * 60)

    except Exception as e:
        print(f"PIPELINE FATAL ERROR: {e}", flush=True)
        log.error("PIPELINE FATAL ERROR: %s", e, exc_info=True)


# -------------------------------------------------------------------------
# DM-event RFI pipeline
# -------------------------------------------------------------------------

async def process_dm_rfi_event(
    project_id: str,
    display_name: str,
    _resource_urn: str,
    app,
):
    from integrations.acc_client import ACCClient

    log.info("DM-triggered RFI lookup (project=%s, item=%r)", project_id, display_name)

    try:
        acc = ACCClient()
        rfis = await acc.list_rfis(project_id=project_id, limit=25)
        if not rfis:
            log.warning("No RFIs returned from ACC -- nothing to process")
            return

        matched_rfi = None
        if display_name:
            dn_lower = display_name.lower()
            for rfi in rfis:
                if dn_lower in (rfi.get("title") or "").lower():
                    matched_rfi = rfi
                    break

        rfi_data = matched_rfi or rfis[0]
        rfi_id   = rfi_data.get("id") or rfi_data.get("rfiId") or ""
        log.info("Using RFI: %r  id=%s", rfi_data.get('title', '(no title)'), rfi_id)

        if not rfi_id:
            log.warning("RFI has no ID -- skipping")
            return

        await process_rfi_event(
            rfi_id=rfi_id,
            project_id=project_id,
            rfi_inline=rfi_data,
            app=app,
        )

    except Exception as e:
        log.error("DM RFI lookup error: %s", e, exc_info=True)


# -------------------------------------------------------------------------
# Fireflies -- legacy transcript workflow
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
    """Legacy pipeline: transcript -> extract -> propose -> score -> notify."""
    from services.normalization import NormalizationService
    from services.proposal_generator import ProposalGenerator
    from services.confidence_scorer import ConfidenceScorer
    from models.database import SessionLocal, Proposal

    log.info("Processing transcript: %r", title)
    try:
        normalizer = NormalizationService()
        extracted = await normalizer.extract(transcript)
        log.info("Extracted: %s -> %s", extracted.get('material_from', '?'), extracted.get('material_to', '?'))

        if not normalizer.is_actionable(extracted):
            log.warning("Transcript not actionable, skipping")
            return

        generator = ProposalGenerator()
        proposal_record = await generator.generate(extracted, meeting_title=title)
        log.info("Proposal: %s", proposal_record['title'])

        scorer = ConfidenceScorer()
        confidence = scorer.score(proposal_record.get("proposal_data", {}), extracted)
        proposal_record["confidence"] = confidence
        log.info("Confidence: %.0f%% (%s)", confidence * 100, scorer.label(confidence))

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

        log.info("Transcript pipeline complete!")

    except Exception as e:
        log.error("Transcript pipeline error: %s", e, exc_info=True)
