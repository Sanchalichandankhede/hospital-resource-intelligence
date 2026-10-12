import pytest
from fastapi.testclient import TestClient
from datetime import date

from backend.main import app
from backend.database import get_db, Base, engine
from backend.models.db_models import (
    User, BedRecord, OxygenRecord, BloodRecord, StaffRecord, AmbulanceRecord,
    Dataset, DataEntry
)

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Setup fresh tables
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    
    # Create test users with roles
    admin = User(username="admin_user", email="admin@hri.org", password_hash="hash", role="ADMIN")
    planner = User(username="planner_user", email="planner@hri.org", password_hash="hash", role="PLANNER")
    viewer = User(username="viewer_user", email="viewer@hri.org", password_hash="hash", role="VIEWER")
    
    db.add_all([admin, planner, viewer])
    db.commit()
    
    yield
    # Cleanup
    Base.metadata.drop_all(bind=engine)

def get_auth_header(username: str):
    # Mock token generation or bypass using direct authorization headers (or mock dependency)
    # The current auth router uses OAuth2PasswordBearer. For testing simplicity, we can fetch
    # actual access tokens from the login endpoint.
    # Let's seed users with real passwords in setup_db or mock them.
    pass

@pytest.fixture(scope="module")
def auth_tokens():
    # Seed proper user passwords
    db = next(get_db())
    from backend.routers.auth import get_password_hash
    
    admin = db.query(User).filter_by(username="admin_user").first()
    admin.password_hash = get_password_hash("Admin123")
    
    planner = db.query(User).filter_by(username="planner_user").first()
    planner.password_hash = get_password_hash("Planner123")
    
    viewer = db.query(User).filter_by(username="viewer_user").first()
    viewer.password_hash = get_password_hash("Viewer123")
    
    db.commit()

    # Get tokens
    admin_token = client.post("/api/auth/login", data={"username": "admin_user", "password": "Admin123"}).json()["access_token"]
    planner_token = client.post("/api/auth/login", data={"username": "planner_user", "password": "Planner123"}).json()["access_token"]
    viewer_token = client.post("/api/auth/login", data={"username": "viewer_user", "password": "Viewer123"}).json()["access_token"]
    
    return {
        "ADMIN": {"Authorization": f"Bearer {admin_token}"},
        "PLANNER": {"Authorization": f"Bearer {planner_token}"},
        "VIEWER": {"Authorization": f"Bearer {viewer_token}"}
    }

# --- Bed Records Validation Tests ---

def test_create_bed_record_valid(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "bed_type": "ICU Beds",
        "available_count": 50,
        "occupied_count": 15,
        "required_count": 20
    }
    response = client.post("/api/resources/beds", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    data = response.json()
    assert data["bed_type"] == "ICU Beds"
    assert data["available_count"] == 50
    assert data["source_type"] == "PLANNER_ENTERED"

def test_create_bed_record_decimal_rejection(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "bed_type": "ICU Beds",
        "available_count": 50.5,
        "occupied_count": 15,
        "required_count": 20
    }
    response = client.post("/api/resources/beds", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 422 # Pydantic validation error or custom 400

def test_create_bed_record_negative_rejection(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "bed_type": "ICU Beds",
        "available_count": -5,
        "occupied_count": 15,
        "required_count": 20
    }
    response = client.post("/api/resources/beds", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code in [400, 422]

def test_create_bed_record_invalid_date(auth_tokens):
    payload = {
        "date": "invalid-date",
        "bed_type": "ICU Beds",
        "available_count": 50,
        "occupied_count": 15,
        "required_count": 20
    }
    response = client.post("/api/resources/beds", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 400

# --- Role Authorization Tests ---

def test_viewer_role_blocked_from_writing(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "bed_type": "ICU Beds",
        "available_count": 50,
        "occupied_count": 15,
        "required_count": 20
    }
    response = client.post("/api/resources/beds", json=payload, headers=auth_tokens["VIEWER"])
    assert response.status_code == 403 # Forbidden

def test_planner_role_blocked_from_deleting(auth_tokens):
    response = client.delete("/api/resources/beds/1", headers=auth_tokens["PLANNER"])
    assert response.status_code == 403

def test_admin_role_allowed_to_delete(auth_tokens):
    # Insert record first
    payload = {
        "date": "2026-08-31",
        "bed_type": "ICU Beds",
        "available_count": 50,
        "occupied_count": 15,
        "required_count": 20
    }
    rec_id = client.post("/api/resources/beds", json=payload, headers=auth_tokens["PLANNER"]).json()["id"]
    
    # Delete as admin
    response = client.delete(f"/api/resources/beds/{rec_id}", headers=auth_tokens["ADMIN"])
    assert response.status_code == 204

# --- Resource-Specific Form Fields Validation ---

def test_oxygen_cylinder_form_validation(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "total_cylinders": 100,
        "available_cylinders": 60,
        "used_cylinders": 40,
        "filled_refilled": 10,
        "required_cylinders": 50,
        "notes": "Testing notes"
      }
    response = client.post("/api/resources/oxygen", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    data = response.json()
    assert data["total_cylinders"] == 100
    assert data["source_type"] == "PLANNER_ENTERED"

def test_blood_group_wise_validation(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "blood_group": "AB+",
        "available_units": 30,
        "used_units": 10,
        "received_units": 5,
        "reserved_units": 2,
        "required_units": 15
    }
    response = client.post("/api/resources/blood", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    data = response.json()
    assert data["blood_group"] == "AB+"

def test_staff_shifts_validation(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "staff_category": "Nurses",
        "available_count": 45,
        "assigned_count": 40,
        "used_count": 40,
        "required_count": 42,
        "shift": "Night",
        "notes": "Roster details"
    }
    response = client.post("/api/resources/staff", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    assert response.json()["shift"] == "Night"

def test_ambulance_maintenance_validation(auth_tokens):
    payload = {
        "date": "2026-08-31",
        "total_ambulances": 15,
        "available_count": 8,
        "used_count": 5,
        "under_maintenance_count": 2,
        "required_count": 7,
        "notes": "Testing ambulance notes"
    }
    response = client.post("/api/resources/ambulance", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    assert response.json()["under_maintenance_count"] == 2


# --- Provenance & Data Management History Tests (Tests 1 - 8) ---

def test_manual_icu_entry_creates_history_record(auth_tokens):
    payload = {
        "date": "2026-09-01",
        "bed_type": "ICU Beds",
        "available_count": 55,
        "occupied_count": 20,
        "required_count": 25
    }
    response = client.post("/api/resources/beds", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200

    # Verify history record created in Dataset table
    db = next(get_db())
    ds = db.query(Dataset).filter_by(source_type="MANUAL_ENTRY", resource_type="ICU Beds").order_by(Dataset.id.desc()).first()
    assert ds is not None
    assert ds.row_count == 1
    assert ds.validation_status == "VALIDATED"
    assert ds.processing_status == "STORED"
    planner = db.query(User).filter_by(username="planner_user").first()
    assert ds.uploaded_by == planner.id


def test_manual_oxygen_entry_creates_history_record(auth_tokens):
    payload = {
        "date": "2026-09-01",
        "total_cylinders": 120,
        "available_cylinders": 70,
        "used_cylinders": 50,
        "filled_refilled": 15,
        "required_cylinders": 60
    }
    response = client.post("/api/resources/oxygen", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200

    db = next(get_db())
    ds = db.query(Dataset).filter_by(source_type="MANUAL_ENTRY", resource_type="Oxygen").order_by(Dataset.id.desc()).first()
    assert ds is not None
    assert ds.row_count == 1
    assert ds.validation_status == "VALIDATED"


def test_manual_blood_entry_creates_history_record(auth_tokens):
    payload = {
        "date": "2026-09-01",
        "blood_group": "O+",
        "available_units": 40,
        "used_units": 15,
        "received_units": 10,
        "reserved_units": 5,
        "required_units": 20
    }
    response = client.post("/api/resources/blood", json=payload, headers=auth_tokens["PLANNER"])
    assert response.status_code == 200

    db = next(get_db())
    ds = db.query(Dataset).filter_by(source_type="MANUAL_ENTRY", resource_type="Blood").order_by(Dataset.id.desc()).first()
    assert ds is not None
    assert ds.row_count == 1


def test_history_api_returns_manual_entries(auth_tokens):
    response = client.get("/api/data/datasets", headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    datasets = response.json()
    assert len(datasets) > 0

    manual_entries = [d for d in datasets if d["source_type"] == "MANUAL_ENTRY"]
    assert len(manual_entries) >= 3
    for entry in manual_entries:
        assert entry["filename"] == "Manual Entry"
        assert entry["uploaded_by_username"] == "planner_user"
        assert entry["row_count"] == 1
        assert entry["processing_status"] == "SAVED"


def test_history_contains_both_imported_and_manual(auth_tokens):
    # Seed an imported dataset record
    db = next(get_db())
    admin = db.query(User).filter_by(username="admin_user").first()
    imported_ds = Dataset(
        filename="test_bulk_demand.csv",
        source_type="CSV_UPLOAD",
        uploaded_by=admin.id,
        resource_type="Multi-Resource",
        row_count=100,
        validation_status="VALIDATED",
        processing_status="STORED"
    )
    db.add(imported_ds)
    db.commit()

    response = client.get("/api/data/datasets", headers=auth_tokens["ADMIN"])
    assert response.status_code == 200
    datasets = response.json()

    source_types = {d["source_type"] for d in datasets}
    assert "MANUAL_ENTRY" in source_types
    assert "CSV_UPLOAD" in source_types


def test_creator_username_stored_properly(auth_tokens):
    # Create as admin
    payload = {
        "date": "2026-09-02",
        "bed_type": "General Beds",
        "available_count": 100,
        "occupied_count": 60,
        "required_count": 70
    }
    res_admin = client.post("/api/resources/beds", json=payload, headers=auth_tokens["ADMIN"])
    assert res_admin.status_code == 200

    response = client.get("/api/data/datasets", headers=auth_tokens["ADMIN"])
    assert response.status_code == 200
    datasets = response.json()

    # The latest entry should be uploaded by admin_user
    latest = datasets[0]
    assert latest["source_type"] == "MANUAL_ENTRY"
    assert latest["uploaded_by_username"] == "admin_user"
    assert latest["resource_type"] == "General Beds"


def test_invalid_manual_entry_does_not_create_history_record(auth_tokens):
    db = next(get_db())
    count_before = db.query(Dataset).count()

    invalid_payload = {
        "date": "2026-09-03",
        "bed_type": "ICU Beds",
        "available_count": -10,  # Negative count -> invalid
        "occupied_count": 10,
        "required_count": 10
    }
    response = client.post("/api/resources/beds", json=invalid_payload, headers=auth_tokens["PLANNER"])
    assert response.status_code in [400, 422]

    db = next(get_db())
    count_after = db.query(Dataset).count()
    assert count_after == count_before


def test_newest_history_entries_appear_first(auth_tokens):
    response = client.get("/api/data/datasets", headers=auth_tokens["PLANNER"])
    assert response.status_code == 200
    datasets = response.json()

    # Verify descending ordering by checking id or upload time
    ids = [d["id"] for d in datasets]
    assert ids == sorted(ids, reverse=True)

