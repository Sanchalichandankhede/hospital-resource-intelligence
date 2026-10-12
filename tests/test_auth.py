import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set testing flag in env
os.environ["TESTING"] = "True"

from backend.main import app
from backend.database import Base, get_db
from backend.models.db_models import User
from database.load_data import load_all_data

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    from backend.database import engine
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        load_all_data(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def get_auth_headers(username, password):
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_login_success():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "AdminPassword123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["username"] == "admin"
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]

def test_login_invalid():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "WrongPassword"}
    )
    assert response.status_code == 401

def test_auth_me_endpoint():
    headers = get_auth_headers("admin", "AdminPassword123")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == "ADMIN"
    assert "password_hash" not in data

def test_unauthorized_protected_endpoint():
    # Attempting to fetch user info without token
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_admin_role_authorization():
    # Admin tries to register a new user
    headers = get_auth_headers("admin", "AdminPassword123")
    response = client.post(
        "/api/auth/register",
        json={
            "username": "new_planner",
            "email": "new_planner@example.com",
            "password": "PlannerPassword123",
            "role": "PLANNER"
        },
        headers=headers
    )
    assert response.status_code == 201
    assert response.json()["username"] == "new_planner"

def test_planner_role_forbidden_action():
    # Planner tries to register a new user (forbidden)
    headers = get_auth_headers("planner", "PlannerPassword123")
    response = client.post(
        "/api/auth/register",
        json={
            "username": "another_viewer",
            "email": "another_viewer@example.com",
            "password": "ViewerPassword123",
            "role": "VIEWER"
        },
        headers=headers
    )
    assert response.status_code == 403

def test_viewer_role_forbidden_action():
    # Viewer tries to register a new user (forbidden)
    headers = get_auth_headers("viewer", "ViewerPassword123")
    response = client.post(
        "/api/auth/register",
        json={
            "username": "third_viewer",
            "email": "third_viewer@example.com",
            "password": "ViewerPassword123",
            "role": "VIEWER"
        },
        headers=headers
    )
    assert response.status_code == 403

def test_inactive_user_rejection():
    # First Admin disables a user
    from backend.database import SessionLocal
    db = SessionLocal()
    user = db.query(User).filter_by(username="viewer").first()
    user.is_active = False
    db.commit()
    db.close()

    # Viewer tries to login now
    response = client.post(
        "/api/auth/login",
        data={"username": "viewer", "password": "ViewerPassword123"}
    )
    assert response.status_code == 400
