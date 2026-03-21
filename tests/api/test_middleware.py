"""Tests for CORS and APIKey middleware."""
import os
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import add_middleware


def _build_test_app():
    app = FastAPI()

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/test")
    async def test_endpoint():
        return {"data": "secret"}

    add_middleware(app)
    return app


def test_health_always_passes_with_api_key():
    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    with patch.dict(os.environ, {"API_KEY": "secret-key"}):
        resp = client.get("/api/health")
        assert resp.status_code == 200


def test_wrong_api_key_returns_401():
    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    with patch.dict(os.environ, {"API_KEY": "secret-key"}):
        resp = client.get("/api/test", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401
        assert resp.json()["error"] == "Unauthorized"


def test_correct_api_key_returns_200():
    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    with patch.dict(os.environ, {"API_KEY": "secret-key"}):
        resp = client.get("/api/test", headers={"X-API-Key": "secret-key"})
        assert resp.status_code == 200


def test_no_api_key_env_all_pass():
    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)
    env = {k: v for k, v in os.environ.items() if k != "API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        resp = client.get("/api/test")
        assert resp.status_code == 200
