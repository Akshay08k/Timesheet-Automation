"""API tests for authentication, drafts, and endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "DevTimesheet"
    assert "gemini_model" in data


def test_user_registration_and_login():
    # Register test user
    username = "testdev1"
    email = "testdev1@example.com"
    password = "SuperSecretPassword123"

    reg_resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": "Test Developer",
            "password": password,
            "timezone": "Asia/Kolkata",
        },
    )
    assert reg_resp.status_code in (200, 400)  # 400 if rerun

    # Login
    login_resp = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    token = token_data["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # /api/auth/me
    me_resp = client.get("/api/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == username

    # /api/timesheets/week/2026-10-26 (Monday)
    week_resp = client.get("/api/timesheets/week/2026-10-26", headers=auth_headers)
    assert week_resp.status_code == 200
    week_data = week_resp.json()
    assert len(week_data["entries"]) == 5
    assert week_data["week_start"] == "2026-10-26"
    assert week_data["entries"][0]["day_of_week"] == "Monday"
    assert week_data["entries"][4]["day_of_week"] == "Friday"
