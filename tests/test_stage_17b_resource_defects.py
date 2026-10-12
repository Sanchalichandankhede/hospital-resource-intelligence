import os
import sys
import math
import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "True"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.database import engine, SessionLocal, Base
from backend.models.db_models import User
from database.load_data import load_all_data

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_all_data(db)
        
        # Add test user if not existing
        from backend.routers.auth import get_password_hash
        if not db.query(User).filter_by(username="tester17b").first():
            test_user = User(
                username="tester17b",
                email="tester17b@hri.org",
                password_hash=get_password_hash("TestPass123"),
                role="ADMIN"
            )
            db.add(test_user)
            db.commit()
    finally:
        db.close()
    
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    db_file = "test.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass

@pytest.fixture(scope="module")
def auth_header():
    resp = client.post("/api/auth/login", data={"username": "tester17b", "password": "TestPass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_multi_resource_oxygen_canonical_contract(auth_header):
    """
    Verify Oxygen Demand uses canonical 100.0 Liters capacity,
    unit 'Liters', formula (15 * ICU + 1.25 * ED), and continuous
    float operational requirements (no unconditional Math.ceil).
    """
    resp = client.get("/api/forecast/multi?model=XGBoost")
    assert resp.status_code == 200
    data = resp.json()
    assert "Oxygen Demand" in data["resources"]
    
    oxy = data["resources"]["Oxygen Demand"]
    assert oxy["unit"] == "Liters"
    assert oxy["is_simulated"] is True
    
    # Fetch underlying ICU and ED forecasts to verify formula
    icu_resp = client.get("/api/forecast/icu?model=XGBoost")
    ed_resp = client.get("/api/forecast/ed?model=XGBoost")
    assert icu_resp.status_code == 200
    assert ed_resp.status_code == 200
    
    icu_preds = icu_resp.json()["predictions"]
    ed_preds = ed_resp.json()["predictions"]
    
    for i, p in enumerate(oxy["predictions"]):
        expected_capacity = 100.0
        assert p["capacity"] == expected_capacity
        
        icu_val = icu_preds[i]["predicted_demand"]
        ed_val = ed_preds[i]["predicted_demand"]
        expected_pred = round((icu_val * 15.0) + (ed_val * 0.25 * 5.0), 4)
        
        assert abs(p["predicted_demand"] - expected_pred) < 1e-3
        # Continuous operational requirement (not integer ceiled)
        assert isinstance(p["operational_requirement"], float)
        assert abs(p["operational_requirement"] - p["predicted_demand"]) < 1e-4
        # Operational gap is continuous
        expected_gap = round(expected_capacity - p["operational_requirement"], 4)
        assert abs(p["operational_gap"] - expected_gap) < 1e-3

def test_multi_resource_blood_canonical_contract(auth_header):
    """
    Verify Blood Demand uses canonical 10.0 Units capacity,
    unit 'Units', formula (0.20 * ED arrivals), and discrete
    operational requirement (math.ceil).
    """
    resp = client.get("/api/forecast/multi?model=XGBoost")
    assert resp.status_code == 200
    data = resp.json()
    assert "Blood Demand" in data["resources"]
    
    blood = data["resources"]["Blood Demand"]
    assert blood["unit"] == "Units"
    assert blood["is_simulated"] is True
    
    ed_resp = client.get("/api/forecast/ed?model=XGBoost")
    ed_preds = ed_resp.json()["predictions"]
    
    for i, p in enumerate(blood["predictions"]):
        expected_capacity = 10.0
        assert p["capacity"] == expected_capacity
        
        ed_val = ed_preds[i]["predicted_demand"]
        expected_pred = round(ed_val * 0.20, 4)
        assert abs(p["predicted_demand"] - expected_pred) < 1e-3
        
        # Operational requirement must be discrete whole integer
        expected_op = math.ceil(expected_pred) if expected_pred > 0 else 0
        assert p["operational_requirement"] == expected_op
        assert p["operational_gap"] == int(expected_capacity - expected_op)

def test_multi_resource_general_beds_canonical_contract(auth_header):
    """
    Verify General Bed Demand uses canonical 25.0 Beds capacity,
    unit 'Beds', formula (18.0 + 2.0 * ICU demand), and discrete
    operational requirement.
    """
    resp = client.get("/api/forecast/multi?model=XGBoost")
    assert resp.status_code == 200
    data = resp.json()
    assert "General Bed Demand" in data["resources"]
    
    gen_beds = data["resources"]["General Bed Demand"]
    assert gen_beds["unit"] == "Beds"
    assert gen_beds["is_simulated"] is True
    
    icu_resp = client.get("/api/forecast/icu?model=XGBoost")
    icu_preds = icu_resp.json()["predictions"]
    
    for i, p in enumerate(gen_beds["predictions"]):
        expected_capacity = 25.0
        assert p["capacity"] == expected_capacity
        
        icu_val = icu_preds[i]["predicted_demand"]
        expected_pred = round(18.0 + (icu_val * 2.0), 4)
        assert abs(p["predicted_demand"] - expected_pred) < 1e-3
        
        expected_op = math.ceil(expected_pred) if expected_pred > 0 else 0
        assert p["operational_requirement"] == expected_op
        assert p["operational_gap"] == int(expected_capacity - expected_op)

def test_multi_resource_across_different_models(auth_header):
    """
    Verify multi-resource calculations dynamically work across
    all supported models (XGBoost, Prophet, LSTM).
    """
    for model_name in ["XGBoost", "Prophet", "LSTM"]:
        resp = client.get(f"/api/forecast/multi?model={model_name}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == model_name
        assert len(data["resources"]) == 7
        for r_name in ["ICU Demand", "General Bed Demand", "Emergency Bed Demand", 
                       "Oxygen Demand", "Blood Demand", "Staff Requirement", "Ambulance Requirement"]:
            assert r_name in data["resources"]
            assert len(data["resources"][r_name]["predictions"]) > 0
