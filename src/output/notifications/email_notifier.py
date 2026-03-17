"""Email Notifier (OUT-09): sends fallback notification email via Gmail API."""
import base64
import logging
import os
from email.mime.text import MIMEText

import google.auth.transport.requests
import google.oauth2.credentials
import googleapiclient.discovery

from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)


def notify_email(proposal: Proposal, recipient: str) -> None:
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    if not client_id or not client_secret or not refresh_token:
        logger.info(
            "Gmail credentials not configured — skipping fallback email notification for proposal %s",
            proposal.proposal_id,
        )
        return
    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    score_pct = round(proposal.confidence_score * 100)
    body_text = (
        f"GigAI Proposal Alert\n\n"
        f"Proposal ID: {proposal.proposal_id}\n"
        f"Event ID: {proposal.event_id}\n"
        f"Recommendation: {proposal.recommendation.upper()} (confidence {score_pct}%)\n\n"
        f"Please log in to the GigAI dashboard to review and action this proposal."
    )
    subject = f"[GigAI] Material Change Alert — {proposal.alert.get('title', 'Review Required')}"
    # Blocking Gmail API call — runs synchronously (this notifier is called from sync context)
    creds.refresh(google.auth.transport.requests.Request())
    service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)
    msg = MIMEText(body_text, "plain")
    msg["To"] = recipient
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info("Notification email sent for proposal %s to %s", proposal.proposal_id, recipient)
