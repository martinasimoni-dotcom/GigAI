"""Document Executor (OUT-06): creates drawing markups via ACC Markup API."""
import logging
import os

from src.output.action_gateway import ActionResult
from src.shared.clients import acc as acc_client
from src.shared.models.proposals import Action

logger = logging.getLogger(__name__)


async def execute_document_action(action: Action) -> ActionResult:
    project_id = os.getenv("ACC_PROJECT_ID")
    if not project_id:
        logger.info("ACC credentials not set — skipping drawing markup creation")
        return ActionResult(
            action_type=action.action_type,
            status="success",
            message="Drawing markup skipped (ACC credentials not configured)",
        )
    data = action.action_data or {}
    drawing_number = data.get("drawing_number", "")
    annotation_text = data.get("annotation_text", "")
    version_urn = data.get("version_urn")

    result = acc_client.create_drawing_markup(
        project_id=project_id,
        version_urn=version_urn or "",
        drawing_number=drawing_number,
        annotation_text=annotation_text,
    )
    markup_id = result.get("id", "unknown")
    logger.info("Drawing markup created: %s", markup_id)
    return ActionResult(
        action_type=action.action_type,
        status="success",
        message=f"Drawing markup created: {markup_id}",
    )
