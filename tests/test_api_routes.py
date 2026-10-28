"""API and HTTP integration tests."""
import pytest
from app.config import settings
from tests.conftest import auth_client_for_user

def test_health_endpoints(client):
    r_live = client.get("/health/live")
    assert r_live.status_code == 200
    assert r_live.json()["status"] == "alive"

    r_ready = client.get("/health/ready")
    assert r_ready.status_code == 200
    assert r_ready.json()["status"] == "ready"

def test_login_flow(client, test_users):
    # 1. GET login page
    r_get = client.get("/login")
    assert r_get.status_code == 200
    assert "Lake Toba Intelligence Portal" in r_get.text

    # 2. POST with wrong password
    r_fail = client.post("/login", data={"username": "test_business_owner", "password": "WrongPassword"})
    assert r_fail.status_code == 400
    assert "Invalid username or password" in r_fail.text

    # 3. POST with correct password
    r_succ = client.post(
        "/login",
        data={"username": "test_business_owner", "password": "Password123!"},
        follow_redirects=False
    )
    assert r_succ.status_code == 303
    set_cookie_header = r_succ.headers.get("set-cookie", "")
    assert settings.SESSION_COOKIE_NAME in set_cookie_header

def test_unauthenticated_protected_route(client):
    r = client.get("/datasets")
    assert r.status_code == 401 or r.status_code in (302, 303)

def test_authenticated_dashboard_access(client, db_session, test_users, seeded_dataset):
    user = test_users["business_owner"]
    auth_client_for_user(client, db_session, user)

    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Regional Tourism Performance Overview" in r.text
    assert "Parapat" in r.text

def test_csrf_protection_on_state_change(client, db_session, test_users):
    user = test_users["business_owner"]
    auth_client_for_user(client, db_session, user)

    # State-changing POST without CSRF token
    r = client.post("/datasets/commit", data={"dataset_name": "No CSRF Test"})
    assert r.status_code in (401, 403)
