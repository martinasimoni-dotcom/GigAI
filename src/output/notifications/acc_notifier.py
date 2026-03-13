"""ACC Notifier (OUT-08): sends in-app ACC notifications."""
import logging
import os

from src.shared.clients import acc as acc_client
from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)


def notify_acc(proposal: Proposal) -> None:
    account_id = os.getenv("ACC_ACCOUNT_ID")
    project_id = os.getenv("ACC_PROJECT_ID")
    if not account_id or not project_id:
        raise RuntimeError(
            "ACC_ACCOUNT_ID and ACC_PROJECT_ID must be set in .env to send ACC notifications"
        )
    score_pct = round(proposal.confidence_score * 100)
    subject = proposal.alert.get("title", "GigAI Material Change Alert")
    body = (
        f"Recommendation: {proposal.recommendation.upper()} "
        f"(confidence {score_pct}%)\n\n"
        f"Event ID: {proposal.event_id}\n"
        f"Proposal ID: {proposal.proposal_id}"
    )
    acc_client.send_acc_notification(
        account_id=account_id,
        project_id=project_id,
        subject=subject,
        body=body,
        recipient_ids=[],
    )
    logger.info("ACC notification sent for proposal %s", proposal.proposal_id)
