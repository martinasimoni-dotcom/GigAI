"""
Policy engine: load YAML rules and safely evaluate conditions against EnrichedEvent.
DOM-04

No eval() or exec() used anywhere. Condition parsing uses explicit token matching
and ast.literal_eval (for IN-list value parsing only — safe, literals only).
"""
import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.shared.models.config import EventTypeConfig

if TYPE_CHECKING:
    # Only imported for type checker — avoids triggering config.settings singleton at import time.
    # At runtime, EnrichedEvent is received as a parameter, no import needed.
    from src.system.context.enrichment import EnrichedEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------


class PolicyResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    triggered_rules: list[str] = Field(default_factory=list)
    rule_details: list[dict] = Field(default_factory=list)
    escalate: bool = False
    alert_pm: bool = False


# ---------------------------------------------------------------------------
# Internal condition evaluation helpers (NO eval / NO exec)
# ---------------------------------------------------------------------------


def _build_event_fields(event: "EnrichedEvent") -> dict[str, Any]:
    """
    Flatten EnrichedEvent into a plain dict that condition sub-expressions can
    reference by field name. Defaults cover all fields used in demo_project.yaml.
    """
    ne = event.event  # NormalizedEvent
    material_new_lower = (ne.material_new or "").lower()

    return {
        "quantity": ne.quantity if ne.quantity is not None else 0,
        "estimated_cost": ne.estimated_cost if ne.estimated_cost is not None else 0,
        "material_original": (ne.material_original or "").lower(),
        "material_new": material_new_lower,
        # change_type is sourced from event_type (NormalizedEvent does not store change_type
        # separately; callers set event_type to the granular type, e.g. "material_substitution")
        "change_type": (ne.event_type or "").lower(),
        "location": (ne.location or "").lower(),
        # Derived / demo-hardcoded fields
        "element_type": "window",           # inferred for demo; future: from event
        "material_category": "wood" if "wood" in material_new_lower else "other",
        "affects_load_bearing": False,
        "material_in_spec": True,
        "po_issued": False,
        "pm_decision": "",
        "units_occupied": False,
        "on_critical_path": False,
        "schedule_impact_days": 0,
        "floor_number": 3,                  # inferred from "3rd floor" for demo
        "location_type": "exterior",
        "change_affects_unit_interior": False,
    }


_OPERATORS = (">=", "<=", "!=", "==", ">", "<", " IN ")


def _eval_sub(sub: str, fields: dict[str, Any]) -> bool:
    """
    Evaluate a single sub-condition token (no eval/exec).

    Supported forms:
      field OP value          where OP in {==, !=, >, >=, <, <=}
      field IN [list]
      field IN active_construction_zones   (unknown list → False)

    Returns False for any unknown field or malformed expression.
    """
    sub = sub.strip()

    # --- IN operator ---
    in_upper = " IN "
    if in_upper in sub:
        parts = sub.split(in_upper, 1)
        if len(parts) != 2:
            return False
        field_name = parts[0].strip()
        value_str = parts[1].strip()

        if field_name not in fields:
            logger.debug("Unknown field '%s' in IN condition — returning False", field_name)
            return False

        field_val = fields[field_name]

        # value_str must be a Python list literal for safe parsing
        if not value_str.startswith("["):
            logger.debug("IN value '%s' is not a list literal — returning False", value_str)
            return False

        try:
            allowed_list = ast.literal_eval(value_str)  # safe: literals only
        except (ValueError, SyntaxError):
            logger.debug("Cannot parse IN list '%s' — returning False", value_str)
            return False

        # Case-insensitive string membership
        if isinstance(field_val, str):
            return field_val.lower() in [v.lower() if isinstance(v, str) else v for v in allowed_list]
        return field_val in allowed_list

    # --- Comparison operators (ordered: two-char first to avoid partial match) ---
    matched_op: str | None = None
    for op in _OPERATORS:
        if op == " IN ":
            continue
        if op in sub:
            matched_op = op
            break

    if matched_op is None:
        logger.debug("No supported operator found in sub-condition '%s' — returning False", sub)
        return False

    idx = sub.index(matched_op)
    field_name = sub[:idx].strip()
    raw_value = sub[idx + len(matched_op):].strip()

    if field_name not in fields:
        logger.debug("Unknown field '%s' in condition — returning False", field_name)
        return False

    field_val = fields[field_name]

    # Strip surrounding quotes from string literals
    if (raw_value.startswith("'") and raw_value.endswith("'")) or (
        raw_value.startswith('"') and raw_value.endswith('"')
    ):
        raw_value = raw_value[1:-1]

    # Try numeric comparison first
    try:
        lhs = float(field_val)
        rhs = float(raw_value)
        if matched_op == "==":
            return lhs == rhs
        if matched_op == "!=":
            return lhs != rhs
        if matched_op == ">":
            return lhs > rhs
        if matched_op == ">=":
            return lhs >= rhs
        if matched_op == "<":
            return lhs < rhs
        if matched_op == "<=":
            return lhs <= rhs
    except (ValueError, TypeError):
        pass

    # Boolean literal comparison
    bool_map = {"true": True, "false": False}
    if raw_value.lower() in bool_map:
        rhs_bool = bool_map[raw_value.lower()]
        if matched_op == "==":
            return bool(field_val) == rhs_bool
        if matched_op == "!=":
            return bool(field_val) != rhs_bool
        return False

    # String comparison (case-insensitive)
    lhs_str = str(field_val).lower().strip()
    rhs_str = raw_value.lower().strip()

    if matched_op == "==":
        return lhs_str == rhs_str
    if matched_op == "!=":
        return lhs_str != rhs_str

    logger.debug("Unsupported operator '%s' for string values — returning False", matched_op)
    return False


def _evaluate_condition(condition_str: str, event: "EnrichedEvent") -> bool:
    """
    Evaluate a full condition string (AND-joined sub-conditions) safely.

    Returns False on any error (safe default — unknown conditions never fire).
    """
    condition_str = condition_str.strip()
    fields = _build_event_fields(event)

    sub_conditions = condition_str.split(" AND ")

    try:
        for sub in sub_conditions:
            if not _eval_sub(sub, fields):
                return False
        return True
    except Exception:
        logger.exception("Unexpected error evaluating condition '%s' — returning False", condition_str)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_policies(event: "EnrichedEvent", config: EventTypeConfig) -> PolicyResult:
    """
    Load rules from config.rules_file and evaluate each condition against event.

    Returns a PolicyResult with:
      - triggered_rules: list of rule_ids whose conditions evaluated True
      - rule_details:    list of full rule dicts for triggered rules
      - escalate:        True if any triggered rule has priority "critical"
      - alert_pm:        True if any rules triggered

    No eval() or exec() is used; ast.literal_eval is used only for IN-list parsing.
    """
    rules_path = Path(config.rules_file)

    try:
        with rules_path.open("r", encoding="utf-8") as fh:
            yaml_data = yaml.safe_load(fh)
    except FileNotFoundError:
        logger.error("Rules file not found: %s", rules_path)
        return PolicyResult()
    except yaml.YAMLError as exc:
        logger.error("Failed to parse rules YAML %s: %s", rules_path, exc)
        return PolicyResult()

    rules: list[dict] = yaml_data.get("rules", []) if yaml_data else []

    triggered_rules: list[str] = []
    rule_details: list[dict] = []

    for rule in rules:
        rule_id = rule.get("rule_id", "UNKNOWN")
        condition = rule.get("condition", "")

        if not condition:
            logger.debug("Rule %s has no condition — skipping", rule_id)
            continue

        fired = _evaluate_condition(condition, event)
        logger.debug("Rule %s — condition=%r — fired=%s", rule_id, condition, fired)

        if fired:
            triggered_rules.append(rule_id)
            rule_details.append(rule)

    escalate = any(r.get("priority") in ("critical",) for r in rule_details)
    alert_pm = len(triggered_rules) > 0

    return PolicyResult(
        triggered_rules=triggered_rules,
        rule_details=rule_details,
        escalate=escalate,
        alert_pm=alert_pm,
    )
