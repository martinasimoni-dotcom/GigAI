"""Gmail Executor (OUT-04): sends email via Gmail API v1 with OAuth2 refresh token."""
import base64
import logging
import os
from email.mime.text import MIMEText

import google.auth.transport.requests
import google.oauth2.credentials
import googleapiclient.discovery

from src.output.action_gateway import ActionResult
from src.shared.models.proposals import Action

logger = logging.getLogger(__name__)


async def execute_gmail_action(action: Action) -> ActionResult:
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError(
            "GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN must be set in .env"
        )
    data = action.action_data or {}
    to = data.get("to", "")
    subject = data.get("subject", "(no subject)")
    body = data.get("body", "")

    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    creds.refresh(google.auth.transport.requests.Request())
    service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)

    msg = MIMEText(body, "plain")
    msg["To"] = to
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    message_id = result.get("id", "unknown")
    logger.info("Gmail message sent: %s", message_id)
    return ActionResult(
        action_type=action.action_type,
        status="success",
        message=f"Email sent: {message_id}",
    )
