"""
Change Impact Simulator — academically-grounded prediction models.

Uses:
1. Earned Value Analysis (EVA) for schedule impact prediction
2. Monte Carlo simulation for probabilistic completion date ranges
3. Dependency graph analysis for affected stakeholder identification
4. Historical outcome matching from the learning engine

All models follow established project management methodology
(PMI PMBOK, AACE International, DOE/DOD earned value standards).
"""
import logging
import math
import random
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Seed for reproducible Monte Carlo results in testing
_RNG = random.Random(42)


def simulate_change_impact(
    project_id: str,
    change_description: str,
    cost_delta: float = 0.0,
    schedule_delay_days: int = 0,
) -> dict:
    """
    Full impact analysis for a proposed change.

    Returns a comprehensive impact report with:
    - Earned value analysis (schedule performance)
    - Monte Carlo simulation (probabilistic completion dates)
    - Budget impact breakdown
    - Affected stakeholders and downstream tasks
    - Similar past change outcomes
    """
    # Load project and schedule data
    from src.data.projects import get_project
    from src.data.schedules import get_schedule, analyze_schedule

    project = get_project(project_id)
    if not project:
        return {"error": f"Project {project_id} not found"}

    schedule = get_schedule(project_id)
    analysis = analyze_schedule(project_id) if schedule else None

    # 1. Earned Value Analysis
    eva = _earned_value_analysis(project, schedule, schedule_delay_days)

    # 2. Monte Carlo Simulation
    monte_carlo = _monte_carlo_simulation(project, schedule, schedule_delay_days)

    # 3. Budget Impact
    budget_impact = _budget_impact(project, cost_delta)

    # 4. Affected tasks and stakeholders
    affected = _affected_analysis(project_id, schedule, schedule_delay_days)

    # 5. Historical similar changes
    historical = _find_similar_changes(change_description, project_id)

    return {
        "project_id": project_id,
        "project_name": project["name"],
        "change_description": change_description,
        "earned_value": eva,
        "monte_carlo": monte_carlo,
        "budget_impact": budget_impact,
        "affected_tasks": affected["tasks"],
        "affected_stakeholders": affected["stakeholders"],
        "historical_changes": historical,
        "overall_risk": _assess_overall_risk(eva, monte_carlo, budget_impact),
    }


def _earned_value_analysis(project: dict, schedule: list, delay_days: int) -> dict:
    """
    Earned Value Analysis (EVA) per PMI PMBOK Chapter 7.

    EV Metrics:
    - PV (Planned Value): budgeted cost of work scheduled
    - EV (Earned Value): budgeted cost of work performed
    - AC (Actual Cost): actual cost incurred
    - SPI (Schedule Performance Index): EV/PV (< 1.0 = behind schedule)
    - CPI (Cost Performance Index): EV/AC (< 1.0 = over budget)
    - EAC (Estimate at Completion): BAC/CPI
    - ETC (Estimate to Complete): EAC - AC
    - VAC (Variance at Completion): BAC - EAC
    """
    bac = project["budget"]  # Budget at Completion
    completion = project["completion_pct"] / 100.0
    spent = project["spent"]

    # Calculate EV metrics
    pv = bac * completion  # Simplified: assume linear planned progress
    ev = bac * completion
    ac = spent

    # Performance indices
    spi = ev / pv if pv > 0 else 1.0
    cpi = ev / ac if ac > 0 else 1.0

    # With the proposed change delay
    if delay_days > 0 and schedule:
        total_duration = sum(t.get("duration_days", 0) for t in schedule)
        delay_ratio = delay_days / max(total_duration, 1)
        spi_adjusted = spi * (1 - delay_ratio * 0.5)  # Delay degrades SPI
    else:
        spi_adjusted = spi

    # Forecasts
    eac = bac / cpi if cpi > 0 else bac * 1.5
    etc = eac - ac
    vac = bac - eac

    # Schedule forecasts
    original_end = date.fromisoformat(project["end_date"])
    start = date.fromisoformat(project["start_date"])
    total_planned_days = (original_end - start).days
    predicted_duration = int(total_planned_days / spi_adjusted) if spi_adjusted > 0 else total_planned_days + delay_days
    predicted_end = start + timedelta(days=predicted_duration)
    schedule_variance_days = (predicted_end - original_end).days + delay_days

    return {
        "bac": bac,
        "ev": round(ev, 0),
        "pv": round(pv, 0),
        "ac": ac,
        "spi": round(spi, 3),
        "spi_adjusted": round(spi_adjusted, 3),
        "cpi": round(cpi, 3),
        "eac": round(eac, 0),
        "etc": round(etc, 0),
        "vac": round(vac, 0),
        "original_end_date": project["end_date"],
        "predicted_end_date": predicted_end.isoformat(),
        "schedule_variance_days": schedule_variance_days,
        "interpretation": _interpret_eva(spi_adjusted, cpi),
    }


def _interpret_eva(spi: float, cpi: float) -> str:
    """Human-readable interpretation of EVA metrics."""
    parts = []
    if spi < 0.9:
        parts.append(f"Project is significantly behind schedule (SPI={spi:.2f})")
    elif spi < 1.0:
        parts.append(f"Project is slightly behind schedule (SPI={spi:.2f})")
    else:
        parts.append(f"Project is on or ahead of schedule (SPI={spi:.2f})")

    if cpi < 0.9:
        parts.append(f"over budget (CPI={cpi:.2f})")
    elif cpi < 1.0:
        parts.append(f"slightly over budget (CPI={cpi:.2f})")
    else:
        parts.append(f"within budget (CPI={cpi:.2f})")

    return " and ".join(parts) + "."


def _monte_carlo_simulation(
    project: dict,
    schedule: list,
    delay_days: int,
    n_simulations: int = 1000,
) -> dict:
    """
    Monte Carlo simulation for probabilistic completion dates.

    Models task duration uncertainty using triangular distributions
    (PERT estimate: optimistic, most likely, pessimistic) and runs
    N simulations to produce P50, P75, P90 completion date estimates.

    Methodology: AACE International Recommended Practice 44R-08
    """
    if not schedule:
        # Use project-level estimate
        start = date.fromisoformat(project["start_date"])
        end = date.fromisoformat(project["end_date"])
        planned_days = (end - start).days
        remaining_pct = (100 - project["completion_pct"]) / 100.0
        remaining_days = int(planned_days * remaining_pct)

        # Simulate with ±20% uncertainty + delay
        results = []
        for _ in range(n_simulations):
            optimistic = remaining_days * 0.8
            most_likely = remaining_days + delay_days
            pessimistic = remaining_days * 1.4 + delay_days
            # PERT triangular distribution
            simulated = _triangular(optimistic, most_likely, pessimistic)
            finish = date.today() + timedelta(days=int(simulated))
            results.append(finish)
    else:
        # Detailed simulation using task-level data
        active_tasks = [t for t in schedule if t["status"] != "completed"]

        results = []
        for _ in range(n_simulations):
            total_remaining = 0
            for task in active_tasks:
                remaining_pct = (100 - task["pct_complete"]) / 100.0
                base_days = task["duration_days"] * remaining_pct

                # Add delay to affected tasks (those on critical path)
                extra = delay_days if task.get("critical") else 0

                # PERT estimate with ±15-30% uncertainty
                uncertainty = 0.15 if not task.get("critical") else 0.25
                optimistic = base_days * (1 - uncertainty)
                most_likely = base_days + extra
                pessimistic = base_days * (1 + uncertainty * 2) + extra

                simulated_days = max(0, _triangular(optimistic, most_likely, pessimistic))

                # Critical path tasks contribute directly to total
                if task.get("critical"):
                    total_remaining += simulated_days

            finish = date.today() + timedelta(days=int(total_remaining))
            results.append(finish)

    results.sort()

    p50 = results[int(n_simulations * 0.50)]
    p75 = results[int(n_simulations * 0.75)]
    p90 = results[int(n_simulations * 0.90)]
    p10 = results[int(n_simulations * 0.10)]

    original_end = date.fromisoformat(project["end_date"])

    return {
        "n_simulations": n_simulations,
        "p10": p10.isoformat(),
        "p50": p50.isoformat(),
        "p75": p75.isoformat(),
        "p90": p90.isoformat(),
        "original_end": project["end_date"],
        "p50_delay_days": (p50 - original_end).days,
        "p75_delay_days": (p75 - original_end).days,
        "p90_delay_days": (p90 - original_end).days,
        "confidence_interval": f"{p10.isoformat()} to {p90.isoformat()}",
        "methodology": "Monte Carlo with PERT triangular distribution (AACE 44R-08)",
    }


def _triangular(low: float, mode: float, high: float) -> float:
    """PERT triangular distribution sample."""
    low = max(0, low)
    high = max(low + 1, high)
    mode = max(low, min(mode, high))
    return _RNG.triangular(low, high, mode)


def _budget_impact(project: dict, cost_delta: float) -> dict:
    """Budget impact breakdown: direct, indirect, contingency."""
    bac = project["budget"]
    spent = project["spent"]
    remaining = bac - spent

    # Direct cost is the change amount
    direct = cost_delta

    # Indirect costs (overhead, admin) — typically 8-15% of direct
    indirect = abs(cost_delta) * 0.10

    # Contingency impact — draw from remaining contingency (typically 5-10% of BAC)
    contingency_budget = bac * 0.07
    contingency_used = max(0, spent - (bac * 0.93))  # Rough estimate of contingency consumed
    contingency_remaining = max(0, contingency_budget - contingency_used)

    total_impact = direct + indirect
    contingency_after = max(0, contingency_remaining - max(0, total_impact))

    return {
        "direct_cost": direct,
        "indirect_cost": round(indirect, 0),
        "total_impact": round(total_impact, 0),
        "budget_before": bac,
        "budget_after": round(bac + total_impact, 0),
        "remaining_before": remaining,
        "remaining_after": round(remaining - total_impact, 0),
        "contingency_remaining": round(contingency_after, 0),
        "pct_of_budget": round(total_impact / bac * 100, 2) if bac > 0 else 0,
    }


def _affected_analysis(project_id: str, schedule: list, delay_days: int) -> dict:
    """Identify affected tasks and stakeholders."""
    affected_tasks = []
    if schedule:
        for task in schedule:
            if task["status"] == "completed":
                continue
            if task.get("critical") and delay_days > 0:
                affected_tasks.append({
                    "task_id": task["task_id"],
                    "name": task["name"],
                    "discipline": task["discipline"],
                    "impact": "delayed" if delay_days > 0 else "none",
                    "original_finish": task["finish"],
                    "predicted_finish": (date.fromisoformat(task["finish"]) + timedelta(days=delay_days)).isoformat(),
                })

    # Get affected stakeholders
    stakeholders = []
    try:
        from src.stakeholders.graph import stakeholder_graph
        chain = stakeholder_graph.get_notification_chain(project_id)
        stakeholders = [
            {"name": s["name"], "role": s["role"], "priority": s["notification_priority"], "reason": s["notification_reason"]}
            for s in chain
        ]
    except Exception:
        pass

    return {"tasks": affected_tasks, "stakeholders": stakeholders}


def _find_similar_changes(description: str, project_id: str) -> list[dict]:
    """Find similar past changes from the learning engine."""
    try:
        from src.intelligence.learning import get_decision_history
        history = get_decision_history(limit=50)
        desc_words = set(description.lower().split())
        similar = []
        for h in history:
            h_words = set(str(h.get("event_type", "")).lower().split())
            if len(desc_words & h_words) >= 2:
                similar.append({
                    "decision": h.get("decision"),
                    "event_type": h.get("event_type"),
                    "confidence_score": h.get("confidence_score"),
                    "overridden": h.get("overridden"),
                    "recorded_at": h.get("recorded_at"),
                })
        return similar[:5]
    except Exception:
        return []


def _assess_overall_risk(eva: dict, monte_carlo: dict, budget: dict) -> dict:
    """Assess overall risk level of the change."""
    risk_score = 0
    factors = []

    # Schedule risk
    if eva["spi_adjusted"] < 0.9:
        risk_score += 30
        factors.append("Schedule significantly behind")
    elif eva["spi_adjusted"] < 1.0:
        risk_score += 15
        factors.append("Schedule slightly behind")

    # Cost risk
    if eva["cpi"] < 0.9:
        risk_score += 30
        factors.append("Cost significantly over budget")
    elif eva["cpi"] < 1.0:
        risk_score += 15
        factors.append("Cost slightly over budget")

    # Monte Carlo risk
    p90_delay = monte_carlo.get("p90_delay_days", 0)
    if p90_delay > 30:
        risk_score += 25
        factors.append(f"P90 shows {p90_delay} days potential delay")
    elif p90_delay > 14:
        risk_score += 15
        factors.append(f"P90 shows {p90_delay} days potential delay")

    # Budget impact risk
    pct = budget.get("pct_of_budget", 0)
    if pct > 5:
        risk_score += 20
        factors.append(f"Change is {pct:.1f}% of total budget")
    elif pct > 2:
        risk_score += 10
        factors.append(f"Change is {pct:.1f}% of total budget")

    risk_score = min(100, risk_score)

    if risk_score >= 70:
        level = "high"
    elif risk_score >= 40:
        level = "medium"
    else:
        level = "low"

    return {
        "score": risk_score,
        "level": level,
        "factors": factors,
        "recommendation": _risk_recommendation(level, factors),
    }


def _risk_recommendation(level: str, factors: list) -> str:
    if level == "high":
        return "HIGH RISK: This change has significant schedule and/or cost implications. Recommend detailed review by PM and project controls before approval."
    elif level == "medium":
        return "MODERATE RISK: Change has some impact but is manageable. Review the Monte Carlo P75/P90 dates and ensure contingency covers the budget delta."
    return "LOW RISK: Change has minimal impact on project performance. Standard approval process is appropriate."
