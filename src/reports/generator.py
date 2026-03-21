"""
Auto-report generator — daily and weekly project reports.

Aggregates data from inbox, decisions, RFIs, schedule analysis,
and budget tracking to produce comprehensive project reports
with AI-identified risks and recommendations.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def generate_daily_digest(project_id: Optional[str] = None) -> dict:
    """
    Generate a daily project digest covering the last 24 hours.

    Includes: activities, decisions made, RFIs updated, risks,
    pending items, and AI recommendations.
    """
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)

    # Gather data from all sources
    inbox_summary = _get_inbox_summary(project_id, yesterday)
    decision_summary = _get_decision_summary(project_id, yesterday)
    rfi_summary = _get_rfi_summary(project_id)
    schedule_health = _get_schedule_health(project_id)
    budget_summary = _get_budget_summary(project_id)

    # AI risk identification
    risks = _identify_risks(inbox_summary, rfi_summary, schedule_health, budget_summary)

    return {
        "report_type": "daily_digest",
        "generated_at": now.isoformat(),
        "period": {"from": yesterday.isoformat(), "to": now.isoformat()},
        "project_id": project_id,
        "project_name": _get_project_name(project_id),
        "sections": {
            "activity_summary": inbox_summary,
            "decisions": decision_summary,
            "rfi_status": rfi_summary,
            "schedule_health": schedule_health,
            "budget_summary": budget_summary,
            "risks": risks,
            "recommendations": _generate_recommendations(risks),
        },
    }


def generate_weekly_report(project_id: Optional[str] = None) -> dict:
    """
    Generate a weekly status report with progress metrics,
    budget tracking, schedule health, and trend analysis.
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    inbox_summary = _get_inbox_summary(project_id, week_ago)
    decision_summary = _get_decision_summary(project_id, week_ago)
    rfi_summary = _get_rfi_summary(project_id)
    schedule_health = _get_schedule_health(project_id)
    budget_summary = _get_budget_summary(project_id)
    risks = _identify_risks(inbox_summary, rfi_summary, schedule_health, budget_summary)

    return {
        "report_type": "weekly_status",
        "generated_at": now.isoformat(),
        "period": {"from": week_ago.isoformat(), "to": now.isoformat()},
        "project_id": project_id,
        "project_name": _get_project_name(project_id),
        "sections": {
            "executive_summary": _generate_executive_summary(inbox_summary, schedule_health, budget_summary),
            "activity_summary": inbox_summary,
            "decisions": decision_summary,
            "rfi_status": rfi_summary,
            "schedule_health": schedule_health,
            "budget_tracking": budget_summary,
            "risks_and_issues": risks,
            "recommendations": _generate_recommendations(risks),
            "next_week_priorities": _get_upcoming_priorities(project_id),
        },
    }


def _get_project_name(project_id: Optional[str]) -> str:
    if not project_id:
        return "All Projects"
    try:
        from src.data.projects import get_project
        p = get_project(project_id)
        return p["name"] if p else project_id
    except Exception:
        return project_id


def _get_inbox_summary(project_id: Optional[str], since: datetime) -> dict:
    try:
        from src.inbox.store import inbox_store
        items, total = inbox_store.list_items(project_id=project_id, limit=10000)
        recent = [i for i in items if i.received_at >= since]
        by_type = {}
        for i in recent:
            by_type[i.comm_type] = by_type.get(i.comm_type, 0) + 1
        escalations = [i.summary for i in recent if i.comm_type == "escalation"]
        return {
            "total_communications": len(recent),
            "by_type": by_type,
            "escalations": escalations,
            "unread_count": sum(1 for i in items if not i.is_read),
        }
    except Exception:
        return {"total_communications": 0, "by_type": {}, "escalations": [], "unread_count": 0}


def _get_decision_summary(project_id: Optional[str], since: datetime) -> dict:
    try:
        from src.decisions.store import decision_store
        decisions, total = decision_store.list_decisions(project_id=project_id, limit=10000)
        recent = [d for d in decisions if d.decided_at >= since]
        return {
            "total_decisions": len(recent),
            "decisions": [{"title": d.title, "decided_by": d.decided_by, "source": d.source} for d in recent[:10]],
        }
    except Exception:
        return {"total_decisions": 0, "decisions": []}


def _get_rfi_summary(project_id: Optional[str]) -> dict:
    try:
        from src.rfi.store import rfi_store
        rfis, total = rfi_store.list_rfis(project_id=project_id, limit=10000)
        by_status = {}
        overdue = 0
        for r in rfis:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            if r.status in ("open", "drafted") and r.age_hours > 72:
                overdue += 1
        return {
            "total_rfis": total,
            "by_status": by_status,
            "overdue_count": overdue,
            "open_count": by_status.get("open", 0) + by_status.get("drafted", 0),
        }
    except Exception:
        return {"total_rfis": 0, "by_status": {}, "overdue_count": 0, "open_count": 0}


def _get_schedule_health(project_id: Optional[str]) -> dict:
    if not project_id:
        return {"status": "N/A — select a project for schedule analysis"}
    try:
        from src.data.schedules import analyze_schedule
        analysis = analyze_schedule(project_id)
        if "error" in analysis:
            return {"status": "No schedule data"}
        return {
            "health_score": analysis["health_score"],
            "total_tasks": analysis["total_tasks"],
            "completed": analysis["completed"],
            "in_progress": analysis["in_progress"],
            "urgent_count": len(analysis.get("urgent_tasks", [])),
            "conflict_count": len(analysis.get("conflicts", [])),
            "prediction_count": len(analysis.get("predictions", [])),
        }
    except Exception:
        return {"status": "Schedule analysis unavailable"}


def _get_budget_summary(project_id: Optional[str]) -> dict:
    if not project_id:
        try:
            from src.data.projects import get_project_stats
            stats = get_project_stats()
            return {
                "total_budget": stats["total_budget"],
                "total_spent": stats["total_spent"],
                "utilization_pct": stats["budget_utilization_pct"],
            }
        except Exception:
            return {}
    try:
        from src.data.projects import get_project
        p = get_project(project_id)
        if not p:
            return {}
        return {
            "budget": p["budget"],
            "spent": p["spent"],
            "remaining": p["budget"] - p["spent"],
            "utilization_pct": round(p["spent"] / p["budget"] * 100, 1) if p["budget"] > 0 else 0,
            "completion_pct": p["completion_pct"],
        }
    except Exception:
        return {}


def _identify_risks(inbox: dict, rfis: dict, schedule: dict, budget: dict) -> list[dict]:
    """AI-identified risks based on data analysis."""
    risks = []

    # Escalation risk
    if inbox.get("escalations"):
        risks.append({
            "category": "escalation",
            "severity": "high",
            "description": f"{len(inbox['escalations'])} escalation(s) in the reporting period",
            "details": inbox["escalations"][:3],
        })

    # RFI backlog risk
    if rfis.get("overdue_count", 0) > 0:
        risks.append({
            "category": "rfi_backlog",
            "severity": "medium" if rfis["overdue_count"] < 3 else "high",
            "description": f"{rfis['overdue_count']} RFI(s) overdue (open > 72 hours)",
        })

    # Schedule risk
    health = schedule.get("health_score", {})
    if isinstance(health, dict) and health.get("label") in ("at-risk", "concerning", "critical"):
        risks.append({
            "category": "schedule",
            "severity": "high" if health["label"] in ("concerning", "critical") else "medium",
            "description": f"Schedule health is {health['label']} (score: {health.get('score', 'N/A')})",
        })

    if schedule.get("urgent_count", 0) > 0:
        risks.append({
            "category": "urgent_tasks",
            "severity": "medium",
            "description": f"{schedule['urgent_count']} urgent task(s) requiring attention",
        })

    # Budget risk
    utilization = budget.get("utilization_pct", 0)
    completion = budget.get("completion_pct", 0)
    if utilization > 0 and completion > 0 and utilization > completion * 1.15:
        risks.append({
            "category": "budget",
            "severity": "high",
            "description": f"Budget utilization ({utilization:.1f}%) exceeds completion ({completion}%) by >15%",
        })

    return risks


def _generate_recommendations(risks: list) -> list[str]:
    """Generate actionable recommendations based on identified risks."""
    recs = []
    for risk in risks:
        if risk["category"] == "escalation":
            recs.append("Address all escalations within 24 hours — assign owners and set resolution deadlines.")
        elif risk["category"] == "rfi_backlog":
            recs.append("Clear overdue RFIs — prioritize those blocking downstream trades or permit submissions.")
        elif risk["category"] == "schedule":
            recs.append("Review critical path tasks and evaluate acceleration options (overtime, additional crews, resequencing).")
        elif risk["category"] == "budget":
            recs.append("Conduct cost-to-complete review — identify remaining contingency and evaluate value engineering opportunities.")
        elif risk["category"] == "urgent_tasks":
            recs.append("Review urgent tasks with superintendent — confirm resource availability and remove blockers.")
    if not recs:
        recs.append("No immediate actions required. Continue monitoring schedule and budget performance.")
    return recs


def _generate_executive_summary(inbox: dict, schedule: dict, budget: dict) -> str:
    comms = inbox.get("total_communications", 0)
    health = schedule.get("health_score", {})
    health_label = health.get("label", "unknown") if isinstance(health, dict) else "N/A"
    util = budget.get("utilization_pct", 0)
    completion = budget.get("completion_pct", 0)

    return (
        f"This week: {comms} communications processed. "
        f"Schedule health: {health_label}. "
        f"Budget: {util:.1f}% utilized at {completion}% completion."
    )


def _get_upcoming_priorities(project_id: Optional[str]) -> list[str]:
    priorities = []
    try:
        from src.data.schedules import analyze_schedule
        if project_id:
            analysis = analyze_schedule(project_id)
            milestones = analysis.get("upcoming_milestones", [])
            for m in milestones[:5]:
                priorities.append(f"{m['name']} — due {m['finish']}")
    except Exception:
        pass
    if not priorities:
        priorities.append("Review and update project schedule")
    return priorities
