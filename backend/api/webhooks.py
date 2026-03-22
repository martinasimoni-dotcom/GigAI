"""
Webhook receivers — ACC RFI creation events (primary) + Fireflies legacy.

Supported event paths:
  • dm.version.added   (data system) — DM version added; we check whether the
    item looks like an RFI and, if so, fetch it from the ACC RFIs API.
  • rfis.rfi.created / autodesk.construction…:rfis-1.created.v1
    (ACC-native events — used when the ACC entitlement allows them)
"""
import json
import hmac
import hashlib
from fastapi import APIRouter, BackgroundTasks, Request
from models.schemas import FirefliesWebhook, ACCWebhook
from config import settings

router = APIRouter()


# -------------------------------------------------------------------------
# Helpers — event name extraction
# -------------------------------------------------------------------------

def _extract_event(body: dict) -> str:
    """
    Pull the event name out of whatever envelope ACC/APS actually sent.

    ACC uses several envelope shapes depending on the system and API version.
    We probe every known location so a single missed key can't silently drop
    the event.

    Known locations (checked in priority order):
      1. body["payload"]["hook"]["event"]        — DM webhooks (dm.version.added)
      2. body["payload"]["event"]                — ACC-native envelope
      3. body["event"]                           — flat test/legacy envelope
      4. body["eventType"]                       — some older APS events
      5. body["type"]                            — occasional variant
    """
    root_hook = body.get("hook") or {}
    payload   = body.get("payload") or {}
    hook      = payload.get("hook") or {}

    return (
        root_hook.get("event")           # ACC DM: body.hook.event  ← actual format
        or hook.get("event")             # body.payload.hook.event
        or payload.get("event")          # body.payload.event
        or payload.get("eventType")
        or body.get("event")
        or body.get("eventType")
        or body.get("type")
        or ""
    )


def _extract_dm_payload(body: dict) -> dict:
    """
    Return a dict containing the DM event fields (project, folder,
    displayName, ext, resourceUrn).

    ACC sends DM webhooks with the interesting fields at the root level
    (alongside "hook"), NOT nested inside a "payload" key.  We merge root
    + payload so either shape works.
    """
    payload = body.get("payload") or {}
    # Fields may be at root level (actual ACC format) or inside payload
    # (documented/legacy format).  Root values take priority.
    merged = {**payload, **{k: v for k, v in body.items() if k != "hook"}}
    return merged


def _dm_payload_looks_like_rfi(dm_payload: dict) -> bool:
    """
    Return True when a DM version event appears to relate to an RFI.

    Heuristics (any one is sufficient):
      1. ext.type contains "rfi"       e.g. "items:autodesk.bim360:RFI"
      2. displayName contains "rfi"    e.g. "RFI-042 Replace windows"
      3. folder URN contains "rfis"    e.g. "…fs.folder:co.<rfis-folder-id>"
    """
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
# ACC — primary workflow (RFI-triggered)
# -------------------------------------------------------------------------

@router.post("/acc")
async def acc_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive ACC / APS webhook events.

    Every incoming payload is logged in full so we can diagnose envelope
    shape differences between ACC environments (US vs EMEA, API versions).
    """
    try:
        body = await request.json()
    except Exception as exc:
        print(f"❌ ACC webhook: failed to parse JSON body — {exc}")
        return {"status": "error", "detail": "invalid JSON"}

    # ── Always log the full raw payload ──────────────────────────────────
    print("📥 ACC webhook received")
    print(f"   Raw payload:\n{json.dumps(body, indent=2)}")

    # ── Extract event name from wherever ACC put it ───────────────────────
    event = _extract_event(body)
    print(f"   Resolved event: {event!r}")

    if not event:
        print("   ⚠️  Could not resolve event name from any known field.")
        print("       Keys at root level:", list(body.keys()))
        payload = body.get("payload") or {}
        print("       Keys inside payload:", list(payload.keys()))

    # ── Branch 1: Data Management events ─────────────────────────────────
    if event in ("dm.version.added", "dm.folder.created"):
        dm_payload = _extract_dm_payload(body)

        if not _dm_payload_looks_like_rfi(dm_payload):
            display = dm_payload.get("displayName", "(no name)")
            ext_type = (dm_payload.get("ext") or {}).get("type", "")
            print(f"   ↳ Skipping non-RFI DM item: {display!r}  (ext.type={ext_type!r})")
            return {"status": "received", "event": event, "action": "skipped"}

        project_id   = dm_payload.get("project", "")
        display_name = dm_payload.get("displayName", "")
        resource_urn = dm_payload.get("resourceUrn", "")
        print(f"   ↳ RFI item detected: {display_name!r}  (project={project_id})")

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

    # ── Branch 2: ACC-native RFI events ──────────────────────────────────
    try:
        data = ACCWebhook.model_validate(body)
    except Exception as exc:
        print(f"   ⚠️  ACCWebhook schema validation failed: {exc}")
        return {"status": "received", "event": event or "unknown"}

    rfi_data   = data.get_rfi_data()
    project_id = data.get_project_id()

    if "rfi" in event.lower() and "created" in event.lower() and rfi_data:
        print(f"   ↳ ACC-native RFI created: id={rfi_data.id}")
        background_tasks.add_task(
            process_rfi_event,
            rfi_id=rfi_data.id,
            project_id=project_id,
            rfi_inline=rfi_data.model_dump(),
            app=request.app,
        )
        return {"status": "received", "message": f"RFI {rfi_data.id} queued for processing"}

    print(f"   ↳ No handler matched event {event!r} — acknowledged and ignored")
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

    try:
        acc = ACCClient()

        # ── Step 1: Fetch RFI from ACC ────────────────────────────────────────
        print(f"\n[1/8] Fetching RFI from ACC...")
        try:
            rfi_data = await acc.get_rfi(rfi_id, project_id=project_id)
            for k, v in rfi_inline.items():
                if v and not rfi_data.get(k):
                    rfi_data[k] = v
            print(f"  OK  title       = {rfi_data.get('title', '(none)')!r}")
            print(f"       description = {str(rfi_data.get('description',''))[:120]!r}")
            print(f"       assignedTo  = {rfi_data.get('assignedTo')}")
            print(f"       projectId   = {rfi_data.get('projectId')}")
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback; traceback.print_exc(); return

        # ── Step 2: Resolve assignee email ────────────────────────────────────
        print(f"\n[2/8] Resolving assignee email...")
        try:
            assigned_user_email = (
                rfi_data.get("assignedToEmail")
                or await acc.get_user_email(rfi_data.get("assignedTo", ""))
            )
            print(f"  OK  email = {assigned_user_email!r}")
        except Exception as e:
            print(f"  FAILED: {e}")
            assigned_user_email = None

        # ── Step 3: Claude Haiku extraction ──────────────────────────────────
        print(f"\n[3/8] Claude Haiku — extracting material change...")
        try:
            normalizer = NormalizationService()
            extracted = await normalizer.extract_from_rfi(rfi_data)
            print(f"  OK  material_from = {extracted.get('material_from')!r}")
            print(f"       material_to   = {extracted.get('material_to')!r}")
            print(f"       relevant      = {extracted.get('relevant')}")
            print(f"       location      = {extracted.get('location')!r}")
            print(f"       summary       = {str(extracted.get('summary',''))[:100]!r}")
            if extracted.get("error"):
                print(f"  WARN parse error: {extracted.get('raw','')[:200]}")
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback; traceback.print_exc(); return

        # If Haiku returned relevant=False but the title implies a material change,
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
            print(f"  NOTE: Haiku said not relevant but title implies material change — overriding")
            extracted["relevant"] = True
            # Synthesize missing fields from title
            if not extracted.get("material_from"):
                extracted["material_from"] = f"existing {title_lower.replace('change','').replace('replace','').strip() or 'element'}"
            if not extracted.get("material_to"):
                extracted["material_to"] = f"replacement {extracted.get('material_from', 'element')}"
            if not extracted.get("summary"):
                extracted["summary"] = f"Material change: {rfi_data.get('title', '')}"

        actionable = normalizer.is_rfi_actionable(extracted)
        print(f"\n[3b] Actionable check: {actionable}")
        if not actionable:
            print(f"  STOPPING — RFI not actionable (material_from or material_to missing)")
            print(f"  extracted = {extracted}")
            return

        # ── Step 4: Claude Sonnet proposal ───────────────────────────────────
        print(f"\n[4/8] Claude Sonnet — generating proposal...")
        try:
            generator = ProposalGenerator()
            proposal_record = await generator.generate_from_rfi(
                rfi_data=rfi_data,
                extracted=extracted,
                assigned_user_email=assigned_user_email,
            )
            print(f"  OK  title   = {proposal_record['title']!r}")
            print(f"       summary = {str(proposal_record.get('summary',''))[:100]!r}")
            print(f"       cost    = {proposal_record.get('cost')}")
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback; traceback.print_exc(); return

        # ── Step 5: Confidence scoring ────────────────────────────────────────
        print(f"\n[5/8] Scoring confidence...")
        try:
            scorer = ConfidenceScorer()
            confidence = scorer.score(proposal_record.get("proposal_data", {}), extracted)
            proposal_record["confidence"] = confidence
            print(f"  OK  confidence = {confidence:.0%} ({scorer.label(confidence)})")
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback; traceback.print_exc(); return

        # ── Step 6: Send email ────────────────────────────────────────────────
        print(f"\n[6/8] Sending email...")
        email_sent = False
        email_sent_at = None
        if not assigned_user_email:
            print(f"  SKIP — no assignee email")
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
                        f"Cost impact: €{proposal_record.get('cost', 0):,.0f}\n"
                        f"Confidence: {round(confidence * 100)}%\n\n"
                        f"Review & act: {dashboard_url}"
                    ),
                )
                email_sent = True
                email_sent_at = dt.utcnow()
                print(f"  OK  email sent to {assigned_user_email}")
            except Exception as e:
                print(f"  WARN email failed: {e}")

        # ── Step 7: Save to DB ────────────────────────────────────────────────
        print(f"\n[7/8] Saving to database...")
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
                print(f"  OK  proposal {proposal_record['id'][:8]}... saved")
            finally:
                db.close()
        except Exception as e:
            print(f"  FAILED: {e}")
            import traceback; traceback.print_exc(); return

        # ── Step 8: WebSocket broadcast ───────────────────────────────────────
        print(f"\n[8/8] Broadcasting to dashboard...")
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
                print(f"  OK  WebSocket broadcast sent")
            else:
                print(f"  SKIP — no ws_manager on app.state")
        except Exception as e:
            print(f"  WARN WebSocket failed: {e}")

        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETE")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\nPIPELINE FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


# -------------------------------------------------------------------------
# DM-event RFI pipeline
# -------------------------------------------------------------------------

async def process_dm_rfi_event(
    project_id: str,
    display_name: str,
    _resource_urn: str,
    app,
):
    """
    Called when a dm.folder.created / dm.version.added event looks like a
    new RFI.  We query the ACC RFIs API for the most recently created RFI in
    the project and process it through the standard proposal pipeline.

    Why not use the resource_urn directly?  DM item URNs don't map 1-to-1 to
    ACC RFI IDs, so the safest approach is to list recent RFIs and pick the
    newest one whose title matches the DM item's displayName (if available).
    """
    from integrations.acc_client import ACCClient

    print(f"\n🔄 DM-triggered RFI lookup (project={project_id}, item={display_name!r})")

    try:
        acc = ACCClient()

        # Fetch the most recent RFIs from the project (up to 25)
        rfis = await acc.list_rfis(project_id=project_id, limit=25)
        if not rfis:
            print("  ⚠️  No RFIs returned from ACC — nothing to process")
            return

        # Prefer an RFI whose title matches the DM displayName; otherwise use
        # the newest one (ACC returns them newest-first by default).
        matched_rfi = None
        if display_name:
            dn_lower = display_name.lower()
            for rfi in rfis:
                if dn_lower in (rfi.get("title") or "").lower():
                    matched_rfi = rfi
                    break

        rfi_data = matched_rfi or rfis[0]
        rfi_id   = rfi_data.get("id") or rfi_data.get("rfiId") or ""
        print(f"  ↳ Using RFI: {rfi_data.get('title', '(no title)')!r}  id={rfi_id}")

        if not rfi_id:
            print("  ⚠️  RFI has no ID — skipping")
            return

        await process_rfi_event(
            rfi_id=rfi_id,
            project_id=project_id,
            rfi_inline=rfi_data,
            app=app,
        )

    except Exception as e:
        print(f"❌ DM RFI lookup error: {e}")
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
