"""
ACC Facade — tries real ACC API first, falls back to mock on failure.

Import this module instead of acc.py or acc_mock.py directly. On each call:
  1. No ACC credentials? → mock immediately
  2. Credentials configured? → try real API
  3. Real call fails? → log warning, fall back to mock

The system ALWAYS works — seamlessly upgrades to real ACC when credentials are valid.
"""
import logging
import os
from typing import Any

from src.shared.clients import acc as real_acc
from src.shared.clients import acc_mock as mock_acc

logger = logging.getLogger(__name__)


def _acc_available() -> bool:
    return bool(os.getenv("ACC_CLIENT_ID") and os.getenv("ACC_CLIENT_SECRET"))


def _try_real_or_mock(real_fn, mock_fn, *args, **kwargs) -> Any:
    if not _acc_available():
        return mock_fn(*args, **kwargs)
    try:
        return real_fn(*args, **kwargs)
    except Exception as exc:
        logger.warning("Real ACC call %s failed (%s: %s) — falling back to mock", real_fn.__name__, type(exc).__name__, exc)
        return mock_fn(*args, **kwargs)


# ═══ Account Admin ══════════════════════════════════════════════════════════

def get_projects() -> list[dict]:
    return _try_real_or_mock(real_acc.get_projects, mock_acc.get_projects)

def get_project_details(project_id: str | None = None) -> dict:
    return _try_real_or_mock(real_acc.get_project_details, mock_acc.get_project_details, project_id)

def get_project_users(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_project_users, mock_acc.get_project_users, project_id)

def get_companies() -> list[dict]:
    return _try_real_or_mock(real_acc.get_companies, mock_acc.get_companies)

def get_account_users() -> list[dict]:
    return _try_real_or_mock(real_acc.get_account_users, mock_acc.get_account_users)


# ═══ Cost Management ════════════════════════════════════════════════════════

def get_budgets(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_budgets, mock_acc.get_budgets, project_id)

def get_contracts(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_contracts, mock_acc.get_contracts, project_id)

def get_change_orders(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_change_orders, mock_acc.get_change_orders, project_id)

def get_cost_items(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_cost_items, mock_acc.get_cost_items, project_id)


# ═══ Issues ══════════════════════════════════════════════════════════════════

def get_issues(project_id: str | None = None, container_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_issues, mock_acc.get_issues, project_id, container_id)

def create_issue(project_id, container_id, title, description, assignee_id=None, issue_type="task", due_date=None):
    return _try_real_or_mock(real_acc.create_issue, mock_acc.create_issue, project_id, container_id, title, description, assignee_id, issue_type, due_date)


# ═══ RFIs & Submittals ══════════════════════════════════════════════════════

def get_rfis(project_id: str | None = None, container_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_rfis, mock_acc.get_rfis, project_id, container_id)

def get_submittals(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_submittals, mock_acc.get_submittals, project_id)


# ═══ Documents ═══════════════════════════════════════════════════════════════

def get_top_folders(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_top_folders, mock_acc.get_top_folders, project_id)

def get_folder_contents(project_id: str, folder_id: str) -> list[dict]:
    return _try_real_or_mock(real_acc.get_folder_contents, mock_acc.get_folder_contents, project_id, folder_id)


# ═══ Locations ═══════════════════════════════════════════════════════════════

def get_floor_plan(project_id: str, location_query: str | None = None) -> dict:
    return _try_real_or_mock(real_acc.get_floor_plan, mock_acc.get_floor_plan, project_id, location_query)


# ═══ Schedule ════════════════════════════════════════════════════════════════

def get_schedule_activities(project_id: str) -> list[dict]:
    return _try_real_or_mock(real_acc.get_schedule_activities, mock_acc.get_schedule_activities, project_id)


# ═══ Forms / Checklists ══════════════════════════════════════════════════════

def get_checklists(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_checklists, mock_acc.get_checklists, project_id)


# ═══ Photos ══════════════════════════════════════════════════════════════════

def get_photos(project_id: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_photos, mock_acc.get_photos, project_id)


# ═══ Daily Logs ══════════════════════════════════════════════════════════════

def get_daily_logs(project_id: str | None = None, log_date: str | None = None) -> list[dict]:
    return _try_real_or_mock(real_acc.get_daily_logs, mock_acc.get_daily_logs, project_id, log_date)


# ═══ Drawing Markup ══════════════════════════════════════════════════════════

def create_drawing_markup(project_id, version_urn, drawing_number, annotation_text, x=0.0, y=0.0):
    return _try_real_or_mock(real_acc.create_drawing_markup, mock_acc.create_drawing_markup, project_id, version_urn, drawing_number, annotation_text, x, y)


# ═══ Notifications ═══════════════════════════════════════════════════════════

def send_acc_notification(account_id, project_id, subject, body, recipient_ids):
    return _try_real_or_mock(real_acc.send_acc_notification, mock_acc.send_acc_notification, account_id, project_id, subject, body, recipient_ids)


# ═══ Comprehensive Pull ═════════════════════════════════════════════════════

def pull_all_project_data(project_id: str | None = None) -> dict:
    """Pull ALL data from ACC for a project. Falls back to mock per-endpoint."""
    return _try_real_or_mock(real_acc.pull_all_project_data, mock_acc.pull_all_project_data, project_id)


# ═══ Helpers ═════════════════════════════════════════════════════════════════

def get_team_directory() -> list[dict]:
    return _try_real_or_mock(real_acc.get_project_users, mock_acc.get_team_directory)

def get_created_issues() -> list[dict]:
    return mock_acc.get_created_issues()

def is_using_mock() -> bool:
    return not _acc_available()
