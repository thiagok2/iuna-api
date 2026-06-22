"""Integration tests for the IUNA API."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Test client without requiring ES connection (lifespan disabled)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Public endpoints (no auth)
# ---------------------------------------------------------------------------


def test_read_root(client):
    """Root path returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert "Welcome to IUNA API" in json_data["message"]
    assert json_data["docs_url"] == "/docs"


def test_health_check_no_auth_required(client):
    """GET /api/v1/health-check must be public (no auth)."""
    response = client.get("/api/v1/health-check")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert "running" in json_data["message"].lower()


def test_info_no_auth_required(client):
    """GET /api/v1/info must be public (no auth)."""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["name"] == "IUNA API"
    assert "version" in json_data


# ---------------------------------------------------------------------------
# X-Request-Id middleware
# ---------------------------------------------------------------------------


def test_x_request_id_generated(client):
    """All responses must include X-Request-Id header."""
    response = client.get("/api/v1/health-check")
    assert "X-Request-Id" in response.headers
    # Must be a valid UUID-like string (36 chars with dashes)
    assert len(response.headers["X-Request-Id"]) == 36


def test_x_request_id_preserved(client):
    """If client sends X-Request-Id, it should be preserved."""
    custom_id = "my-custom-request-id-123456789012"
    response = client.get(
        "/api/v1/health-check", headers={"X-Request-Id": custom_id}
    )
    assert response.headers["X-Request-Id"] == custom_id


# ---------------------------------------------------------------------------
# Auth-protected endpoints
# ---------------------------------------------------------------------------


def test_health_requires_auth_when_token_configured(client):
    """GET /api/v1/health without token → 401 (when API_SECRET_TOKEN is set)."""
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.API_SECRET_TOKEN = "test-secret"
        response = client.get("/api/v1/health")
    # The actual settings has a token configured via .env, so we expect 401
    assert response.status_code in (401, 403)


def test_health_with_valid_token(client):
    """GET /api/v1/health with valid Bearer token → 200."""
    from app.config import settings

    token = settings.API_SECRET_TOKEN
    if not token:
        pytest.skip("API_SECRET_TOKEN not configured")

    response = client.get(
        "/api/v1/health", headers={"Authorization": f"Bearer {token}"}
    )
    # May be 200 or 503 (if ES is not available), but not 401
    assert response.status_code != 401


def test_health_with_invalid_token(client):
    """GET /api/v1/health with wrong token → 401."""
    from app.config import settings

    if not settings.API_SECRET_TOKEN:
        pytest.skip("API_SECRET_TOKEN not configured, dev mode skips auth")

    response = client.get(
        "/api/v1/health", headers={"Authorization": "Bearer wrong-token"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Dev mode (no API_SECRET_TOKEN)
# ---------------------------------------------------------------------------


def test_health_dev_mode_no_auth_required(client):
    """In dev mode (no API_SECRET_TOKEN), /health should not require auth."""
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.API_SECRET_TOKEN = None
        response = client.get("/api/v1/health")
    # In dev mode, should not be 401
    # Note: may still fail due to ES connectivity, but auth won't block it
    assert response.status_code != 401
