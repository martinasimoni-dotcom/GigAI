"""ACC Executor (OUT-03): creates ACC Issues via real ACC API."""
import logging
import os

from src.output.action_gateway import ActionResult
from src.shared.clients import acc as acc_client
from src.shared.models.proposals import Action

logger = logging.getLogger(__name__)


async def execute_acc_action(action: Action) -> ActionResult:
    project_id = os.getenv("ACC_PROJECT_ID")
    container_id = os.getenv("ACC_ISSUES_CONTAINER_ID")
    if not project_id or not container_id:
        raise RuntimeError(
            "ACC_PROJECT_ID and ACC_ISSUES_CONTAINER_ID must be set in .env"
        )
    data = action.action_data or {}
    title = data.get("title", "GigAI Generated Issue")
    description = data.get("description", "")
    assignee_id = data.get("assignee_id")
    due_date = data.get("due_date")

    issue = acc_client.create_issue(
        project_id=project_id,
        container_id=container_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        due_date=due_date,
    )
    issue_id = issue.get("id", "unknown")
    logger.info("ACC issue created: %s", issue_id)
    return ActionResult(
        action_type=action.action_type,
        status="success",
        message=f"ACC issue created: {issue_id}",
    )
