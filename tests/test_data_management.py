import os
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set testing flag in env
os.environ["TESTING"] = "True"

from backend.main import app
from backend.database import Base, get_db
from backend.models.db_models import DataEntry, User
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

def test_csv_upload_valid():
    headers = get_auth_headers("admin", "AdminPassword123")
    csv_data = "date,resource,value\n2137-10-18,ICU Demand,12.0\n2137-10-18,Oxygen Demand,45.5\n"
    
    response = client.post(
        "/api/data/upload",
        files={"file": ("dataset.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["rows"] == 2
    assert "ICU Demand" in [r["resource"] for r in data["preview"]]

def test_excel_upload_invalid_file_type():
    headers = get_auth_headers("admin", "AdminPassword123")
    response = client.post(
        "/api/data/upload",
        files={"file": ("dataset.txt", io.BytesIO(b"dummy text content"), "text/plain")},
        headers=headers
    )
    assert response.status_code == 400
    assert "Only CSV (.csv) and Excel (.xlsx) are supported." in response.json()["detail"]

def test_csv_upload_missing_columns():
    headers = get_auth_headers("admin", "AdminPassword123")
    csv_data = "date,value\n2137-10-18,12.0\n"
    response = client.post(
        "/api/data/upload",
        files={"file": ("dataset.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "Missing required columns: resource" in response.json()["errors"][0]

def test_csv_upload_invalid_data():
    headers = get_auth_headers("admin", "AdminPassword123")
    # Date invalid format, negative value, unknown resource name
    csv_data = "date,resource,value\nbad-date,ICU Demand,12.0\n2137-10-18,Unknown Resource,10.0\n2137-10-18,ICU Demand,-5.0\n"
    response = client.post(
        "/api/data/upload",
        files={"file": ("dataset.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any("Invalid date format" in e for e in data["errors"])
    assert any("Unknown resource name" in e for e in data["errors"])
    assert any("Negative resource quantity" in e for e in data["errors"])

def test_import_dataset_valid():
    headers = get_auth_headers("admin", "AdminPassword123")
    payload = {
        "entries": [
            {"date": "2137-10-18", "resource": "ICU Demand", "value": 15.0},
            {"date": "2137-10-18", "resource": "Oxygen Demand", "value": 120.0}
        ]
    }
    response = client.post("/api/data/import", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "retraining_notice" in response.json()
    assert response.json()["retraining_triggered"] is False

    # Check that entries exist in DB
    from backend.database import SessionLocal
    db = SessionLocal()
    records = db.query(DataEntry).filter_by(date="2137-10-18", source_type="UPLOADED_DATASET").all()
    assert len(records) == 2
    assert records[0].value in [15.0, 120.0]
    db.close()

def test_import_invalid_dataset():
    headers = get_auth_headers("admin", "AdminPassword123")
    # Negative value
    payload = {
        "entries": [
            {"date": "2137-10-18", "resource": "ICU Demand", "value": -10.0}
        ]
    }
    response = client.post("/api/data/import", json=payload, headers=headers)
    assert response.status_code == 400

def test_manual_entry_valid():
    headers = get_auth_headers("planner", "PlannerPassword123")
    payload = {
        "date": "2137-10-19",
        "icu_demand": 14.0,
        "oxygen_demand": 150.0
    }
    response = client.post("/api/data/manual", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "retraining_notice" in response.json()
    
    # Check that manual entries exist in DB with planner creation id
    from backend.database import SessionLocal
    db = SessionLocal()
    planner_user = db.query(User).filter_by(username="planner").first()
    records = db.query(DataEntry).filter_by(date="2137-10-19", source_type="MANUAL_ENTRY").all()
    assert len(records) == 2
    assert records[0].created_by == planner_user.id
    db.close()

def test_manual_entry_invalid_date():
    headers = get_auth_headers("planner", "PlannerPassword123")
    payload = {
        "date": "bad-date",
        "icu_demand": 14.0
    }
    response = client.post("/api/data/manual", json=payload, headers=headers)
    assert response.status_code == 400

def test_manual_entry_negative_values():
    headers = get_auth_headers("planner", "PlannerPassword123")
    payload = {
        "date": "2137-10-19",
        "icu_demand": -5.0
    }
    response = client.post("/api/data/manual", json=payload, headers=headers)
    assert response.status_code == 400

def test_get_entries_list():
    response = client.get("/api/data/entries")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(d["source_type"] == "MANUAL_ENTRY" for d in data)
    assert any(d["source_type"] == "UPLOADED_DATASET" for d in data)
