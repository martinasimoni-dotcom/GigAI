from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import parse, request
from urllib.error import HTTPError, URLError

from .config import AccReadonlySyncConfig


class AccAuthError(RuntimeError):
    pass


@dataclass(slots=True)
class TokenResponse:
    access_token: str
    expires_in: int | None = None


class AccessTokenProvider:
    def __init__(self, config: AccReadonlySyncConfig) -> None:
        self._config = config

    def get(self) -> str:
        if self._config.access_token:
            return self._config.access_token

        if not (self._config.client_id and self._config.client_secret and self._config.refresh_token):
            raise AccAuthError(
                "ACC access token is not configured. Set ACC_ACCESS_TOKEN or ACC_CLIENT_ID, "
                "ACC_CLIENT_SECRET, and ACC_REFRESH_TOKEN."
            )

        form_data = parse.urlencode(
            {
                "grant_type": "refresh_token",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "refresh_token": self._config.refresh_token,
                "scope": self._config.scopes,
            }
        ).encode("utf-8")
        req = request.Request(
            "https://developer.api.autodesk.com/authentication/v2/token",
            data=form_data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as ex:
            body = ex.read().decode("utf-8") if hasattr(ex, "read") else "(no body)"
            raise AccAuthError(f"Autodesk authentication failed (HTTP {ex.code}): {body}") from ex
        except URLError as ex:
            raise AccAuthError(f"Autodesk authentication failed (network error): {ex.reason}") from ex
        except Exception as ex:
            raise AccAuthError(f"Autodesk authentication failed: {ex}") from ex
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise AccAuthError("Autodesk authentication response did not include access_token.")
        return token

