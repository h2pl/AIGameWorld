"""Smoke test - verify FastAPI app can be created and health endpoint works."""

import pytest
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_app_created():
    """App should be created with correct title."""
    assert app.title == "AIGameWorld API"
    assert app.version == "0.1.0"


def test_health_check(client):
    """Health endpoint should return ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "AIGameWorld-backend"
