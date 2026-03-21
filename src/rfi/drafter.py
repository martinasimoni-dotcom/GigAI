"""
RFI auto-drafter — generates response drafts using the knowledge base.

Uses Claude Sonnet for high-quality responses that cite specific
knowledge base sections and reference past RFIs.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from src.rfi.models import RFI, RFIResponse
from src.rfi.store import rfi_store

logger = logging.getLogger(__name__)

_DRAFT_PROMPT = """You are an expert construction project manager drafting an RFI response.

RFI DETAILS:
Title: {title}
Category: {category}
Project: {project_name}
Priority: {priority}
Requester: {requester}

QUESTION:
{question}

KNOWLEDGE BASE CONTEXT:
{knowledge_context}

PAST SIMILAR RFIs:
{past_rfis}

Draft a professional RFI response that:
1. Directly answers the question with specific technical detail
2. Cites relevant specifications, codes, or standards
3. References the knowledge base sections used
4. Provides a clear recommendation
5. Notes any conditions or caveats

Respond with ONLY valid JSON:
{{
  "response_text": "Your detailed response here. Include specific references to specs, codes, and standards.",
  "knowledge_sources": ["List of knowledge base sections referenced"],
  "confidence": 0.0 to 1.0 (how confident you are in this response)
}}"""


def draft_rfi_response(rfi_id: str) -> Optional[RFI]:
    """
    Generate an AI-drafted response for an RFI.
    Updates the RFI in the store with the draft.
    """
    rfi = rfi_store.get(rfi_id)
    if not rfi:
        return None

    # Get knowledge context
    knowledge_context = _get_knowledge_context(rfi.question, rfi.category)

    # Get past similar RFIs
    past_rfis = _get_past_rfis(rfi.question, rfi.rfi_id)

    prompt = _DRAFT_PROMPT.format(
        title=rfi.title,
        category=rfi.category,
        project_name=rfi.project_name or "N/A",
        priority=rfi.priority,
        requester=rfi.requester,
        question=rfi.question[:2000],
        knowledge_context=knowledge_context,
        past_rfis=past_rfis,
    )

    try:
        from src.shared.llm.claude import call_sonnet
        raw = call_sonnet(
            prompt=prompt,
            system="You are a construction RFI response specialist. Respond with valid JSON only.",
        )

        if isinstance(raw, str):
            parsed = json.loads(raw)
        elif isinstance(raw, dict):
            parsed = raw
        else:
            parsed = json.loads(str(raw))

        response = RFIResponse(
            draft_text=parsed.get("response_text", "Unable to generate response."),
            knowledge_sources=parsed.get("knowledge_sources", []),
            past_rfi_references=[],
            confidence=max(0.0, min(1.0, parsed.get("confidence", 0.5))),
        )

    except Exception as exc:
        logger.warning("RFI draft generation failed (%s), using fallback", exc)
        response = _fallback_draft(rfi)

    # Update the RFI with the response
    updated = rfi_store.update(
        rfi_id,
        response=response,
        status="drafted",
    )

    logger.info("RFI %s drafted — confidence=%.1f%%", rfi_id, response.confidence * 100)
    return updated


def apply_pm_edit(rfi_id: str, edited_text: str) -> Optional[RFI]:
    """
    Apply PM's edits to an RFI draft and record the learning.
    """
    rfi = rfi_store.get(rfi_id)
    if not rfi or not rfi.response:
        return None

    original = rfi.response.draft_text
    updated_response = rfi.response.model_copy(update={
        "pm_edits": edited_text,
        "edited_by_pm": True,
    })

    updated = rfi_store.update(
        rfi_id,
        response=updated_response,
        status="reviewed",
    )

    # Record learning for future improvements (RFI-06)
    _record_rfi_learning(rfi, original, edited_text)

    return updated


def send_rfi(rfi_id: str) -> Optional[RFI]:
    """Mark an RFI as sent."""
    return rfi_store.update(
        rfi_id,
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )


def close_rfi(rfi_id: str) -> Optional[RFI]:
    """Mark an RFI as closed."""
    return rfi_store.update(
        rfi_id,
        status="closed",
        closed_at=datetime.now(timezone.utc),
    )


def _get_knowledge_context(question: str, category: str) -> str:
    """Search the knowledge base for relevant context."""
    try:
        from src.shared.db.vector_store import search
        results = search(question, top_k=3)
        if results:
            return "\n\n".join([f"[{r[2]}] {r[1]}" for r in results])
    except Exception:
        pass

    # Fallback context based on category
    return _fallback_knowledge(category)


def _get_past_rfis(question: str, current_id: str) -> str:
    """Find past RFIs similar to this one."""
    all_rfis, _ = rfi_store.list_rfis(limit=1000)
    past = [r for r in all_rfis if r.rfi_id != current_id and r.response and r.status in ("sent", "closed")]
    if not past:
        return "No past RFIs available for reference."

    # Simple keyword matching for similar past RFIs
    q_words = set(question.lower().split())
    scored = []
    for rfi in past:
        r_words = set(rfi.question.lower().split())
        overlap = len(q_words & r_words) / max(len(q_words), 1)
        if overlap > 0.15:
            scored.append((overlap, rfi))

    scored.sort(key=lambda x: -x[0])
    if not scored:
        return "No similar past RFIs found."

    lines = []
    for _, rfi in scored[:3]:
        resp_text = rfi.response.pm_edits if rfi.response.edited_by_pm else rfi.response.draft_text
        lines.append(f"Past RFI: {rfi.title}\nResponse: {resp_text[:200]}")

    return "\n\n".join(lines)


def _fallback_draft(rfi: RFI) -> RFIResponse:
    """Generate a basic draft when LLM is unavailable."""
    return RFIResponse(
        draft_text=f"RE: {rfi.title}\n\nThank you for your inquiry regarding {rfi.category}. "
                   f"Based on our review of the project specifications and applicable standards, "
                   f"we recommend the following:\n\n"
                   f"[This is an auto-generated draft. Please review the project specifications "
                   f"and applicable building codes for the definitive answer.]\n\n"
                   f"Please do not hesitate to contact us if you need further clarification.",
        knowledge_sources=["Auto-generated — knowledge base search unavailable"],
        confidence=0.3,
    )


def _fallback_knowledge(category: str) -> str:
    """Provide category-specific fallback knowledge."""
    defaults = {
        "fire-protection": "Refer to NFPA 101 Life Safety Code, local building code fire rating requirements, and project specification section 078400 (Firestopping).",
        "structural": "Refer to ACI 318 Building Code Requirements for Structural Concrete, AISC Steel Construction Manual, and project structural drawings.",
        "architectural": "Refer to project architectural specifications, CSI MasterFormat divisions 04-09, and applicable ASTM standards for materials.",
        "MEP": "Refer to ASHRAE 90.1 Energy Standard, NEC (NFPA 70) for electrical, and project MEP specifications.",
        "materials": "Refer to project specification submittals section, ASTM material standards, and approved materials list.",
        "code-compliance": "Refer to International Building Code (IBC), local amendments, and applicable OSHA regulations.",
        "environmental": "Refer to EPA regulations, state environmental guidelines, and project environmental management plan.",
    }
    return defaults.get(category, "Refer to project specifications and applicable building codes.")


def _record_rfi_learning(rfi: RFI, original: str, edited: str) -> None:
    """Record PM edits for future learning (RFI-06)."""
    try:
        from src.intelligence.learning import record_learning
        record_learning(
            proposal_id=rfi.rfi_id,
            decision="rfi_edit",
            reason=f"PM edited RFI response for: {rfi.title}",
            proposal_context={
                "event_type": "rfi_response",
                "category": rfi.category,
                "original_draft": original[:500],
                "pm_edited_version": edited[:500],
            },
        )
    except Exception:
        pass
