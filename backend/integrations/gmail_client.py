"""
Gmail API client — sends emails via OAuth2 refresh token.
Requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN in .env.
"""
import base64
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings


class GmailClient:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    GMAIL_API = "https://gmail.googleapis.com/gmail/v1"

    def _is_configured(self) -> bool:
        return bool(
            settings.GMAIL_CLIENT_ID
            and settings.GMAIL_CLIENT_SECRET
            and settings.GMAIL_REFRESH_TOKEN
        )

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": settings.GMAIL_CLIENT_ID,
                    "client_secret": settings.GMAIL_CLIENT_SECRET,
                    "refresh_token": settings.GMAIL_REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        from_name: str | None = None,
    ) -> dict:
        """Send an email. Falls back to logging if Gmail is not configured."""
        if not self._is_configured():
            print(f"⚠️  Gmail not configured — would email {to}: {subject}")
            return {"status": "logged", "to": to, "subject": subject}

        from_label = from_name or settings.GMAIL_FROM_NAME
        from_addr = settings.GMAIL_FROM_EMAIL

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_label} <{from_addr}>"
        msg["To"] = to

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        access_token = await self._get_access_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.GMAIL_API}/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw},
            )
            resp.raise_for_status()
            result = resp.json()
            print(f"📧 Email sent to {to} — message id: {result.get('id')}")
            return result


def build_proposal_email_html(proposal: dict, dashboard_url: str) -> str:
    """Render a proposal as an HTML email body."""
    title = proposal.get("title", "Material Change Proposal")
    summary = proposal.get("summary", "")
    cost = proposal.get("cost", 0)
    confidence = round((proposal.get("confidence") or 0) * 100)

    proposal_data = proposal.get("proposal_data", {}) or {}
    cost_analysis = proposal_data.get("cost_analysis", {}) or {}
    breakdown = cost_analysis.get("breakdown", []) or []
    risks = proposal_data.get("risks", []) or []

    breakdown_rows = "".join(
        f"<tr><td style='padding:4px 8px;border-bottom:1px solid #e5e7eb'>{b.get('item','')}</td>"
        f"<td style='padding:4px 8px;border-bottom:1px solid #e5e7eb;text-align:right'>€{b.get('cost',0):,.0f}</td></tr>"
        for b in breakdown
    )
    risk_items = "".join(f"<li>{r}</li>" for r in risks)

    conf_color = "#16a34a" if confidence >= 80 else "#d97706"

    return f"""
<!DOCTYPE html><html><body style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;color:#111827">
  <div style="background:linear-gradient(135deg,#1d4ed8,#4338ca);padding:24px;border-radius:12px 12px 0 0">
    <h1 style="color:white;margin:0;font-size:20px">GigAI Material Coordinator</h1>
    <p style="color:#bfdbfe;margin:4px 0 0">New Material Change Proposal</p>
  </div>
  <div style="border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 12px 12px">
    <h2 style="font-size:18px;color:#111827">{title}</h2>
    <p style="color:#6b7280">{summary}</p>

    <div style="display:flex;gap:16px;margin:16px 0">
      <div style="background:#f9fafb;border-radius:8px;padding:12px 16px;flex:1">
        <p style="margin:0;font-size:12px;color:#6b7280">Total Cost Impact</p>
        <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:#111827">€{cost:,.0f}</p>
      </div>
      <div style="background:#f9fafb;border-radius:8px;padding:12px 16px;flex:1">
        <p style="margin:0;font-size:12px;color:#6b7280">Confidence Score</p>
        <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:{conf_color}">{confidence}%</p>
      </div>
    </div>

    {'<h3 style="font-size:14px;color:#374151;margin-bottom:8px">Cost Breakdown</h3><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr><th style="text-align:left;padding:4px 8px;background:#f3f4f6">Item</th><th style="text-align:right;padding:4px 8px;background:#f3f4f6">Cost</th></tr></thead><tbody>' + breakdown_rows + '</tbody></table>' if breakdown_rows else ''}

    {'<h3 style="font-size:14px;color:#374151;margin-top:16px">Risks</h3><ul style="font-size:13px;color:#6b7280;padding-left:20px">' + risk_items + '</ul>' if risks else ''}

    <div style="margin-top:24px;display:flex;gap:12px">
      <a href="{dashboard_url}" style="background:#2563eb;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">View in Dashboard</a>
    </div>
    <p style="font-size:11px;color:#9ca3af;margin-top:24px">Sent by GigAI · Reply to this email to respond</p>
  </div>
</body></html>"""
