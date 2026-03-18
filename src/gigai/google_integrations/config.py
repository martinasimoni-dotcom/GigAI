from __future__ import annotations

import os
from dataclasses import dataclass


def _env(*keys: str) -> str:
    for key in keys:
        value = (os.getenv(key) or "").strip()
        if value:
            return value
    return ""


def _env_bool(default: bool, *keys: str) -> bool:
    value = _env(*keys)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GoogleIntegrationConfig:
    enabled: bool
    gmail_client_id: str
    gmail_client_secret: str
    gmail_refresh_token: str
    calendar_id: str
    sender_user_id: str
    default_recipients: tuple[str, ...]

    @property
    def has_credentials(self) -> bool:
        return bool(self.gmail_client_id and self.gmail_client_secret and self.gmail_refresh_token)

    @classmethod
    def from_env(cls) -> "GoogleIntegrationConfig":
        recipients_raw = _env("GIGAI_NOTIFICATION_EMAILS", "GIGAI_GOOGLE_NOTIFICATION_EMAILS")
        recipients = tuple(
            email.strip()
            for email in recipients_raw.split(",")
            if email.strip()
        )

        return cls(
            enabled=_env_bool(True, "GIGAI_GOOGLE_INTEGRATION_ENABLED", "GIGAI_GOOGLE_CALENDAR_ENABLED"),
            gmail_client_id=_env("GMAIL_CLIENT_ID", "GIGAI_GMAIL_CLIENT_ID"),
            gmail_client_secret=_env("GMAIL_CLIENT_SECRET", "GIGAI_GMAIL_CLIENT_SECRET"),
            gmail_refresh_token=_env("GMAIL_REFRESH_TOKEN", "GIGAI_GMAIL_REFRESH_TOKEN"),
            calendar_id=_env("GOOGLE_CALENDAR_ID", "GIGAI_GOOGLE_CALENDAR_ID") or "primary",
            sender_user_id=_env("GIGAI_GMAIL_USER", "GIGAI_GMAIL_SENDER") or "me",
            default_recipients=recipients,
        )
