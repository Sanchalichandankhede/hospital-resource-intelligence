#!/usr/bin/env python3
import os
import sys

# Ensure testing flag is set in env before imports
os.environ["TESTING"] = "True"

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import engine, SessionLocal, Base
from database.load_data import load_all_data

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """
    Creates and seeds an in-memory SQLite database for testing.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_all_data(db)
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

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert "database" in json_data
    # Verify custom warning header
    assert "x-clinical-notice" in response.headers
    assert "Operational metrics only" in response.headers["x-clinical-notice"]

def test_forecast_icu_valid():
    response = client.get("/api/forecast/icu?model=XGBoost")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"] == "ICU Beds"
    assert data["model"] == "XGBoost"
    assert len(data["predictions"]) > 0
    
    first = data["predictions"][0]
    assert "date" in first
    assert "predicted_demand" in first
    assert "actual_demand" in first

def test_forecast_ed_valid():
    response = client.get("/api/forecast/ed?model=XGBoost")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"] == "ED Arrivals"
    assert len(data["predictions"]) > 0

def test_forecast_invalid_params():
    # Invalid date format
    response = client.get("/api/forecast/icu?start_date=2026-08-xx")
    assert response.status_code == 400
    assert "Invalid start_date format" in response.json()["detail"]

    # Start date after end date
    response = client.get("/api/forecast/icu?start_date=2026-08-28&end_date=2026-08-20")
    assert response.status_code == 400
    assert "start_date cannot be after end_date" in response.json()["detail"]

def test_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert len(data["alerts"]) > 0
    
    # Check simulated capacity safety variables
    alert = data["alerts"][0]
    assert alert["is_capacity_simulated"] is True
    assert alert["actual_capacity"] is None
    assert alert["simulated_capacity"] > 0

def test_alerts_filtering():
    # Filter by resource
    response = client.get("/api/alerts?resource=ICU Beds")
    assert response.status_code == 200
    for a in response.json()["alerts"]:
        assert a["resource"] == "ICU Beds"

    # Filter by risk
    response = client.get("/api/alerts?risk_level=low")
    assert response.status_code == 200
    for a in response.json()["alerts"]:
        assert a["risk_level"] == "LOW"

    # Invalid risk level
    response = client.get("/api/alerts?risk_level=super_high")
    assert response.status_code == 400

def test_recommendations_endpoint():
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    
    rec = data["recommendations"][0]
    assert "recommendation" in rec
    assert "trigger" in rec
    assert "risk_level" in rec

def test_explanations_icu():
    response = client.get("/api/explanations/icu?method=SHAP")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"] == "ICU Beds"
    assert data["explanation_method"] == "SHAP"
    assert len(data["explanations"]) > 0
    
    first = data["explanations"][0]
    assert "feature" in first
    assert "contribution" in first
    assert "direction" in first

def test_explanations_ed():
    response = client.get("/api/explanations/ed?method=LIME")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"] == "ED Arrivals"
    assert data["explanation_method"] == "LIME"
    assert len(data["explanations"]) > 0

def test_explanations_invalid_method():
    response = client.get("/api/explanations/icu?method=INVALID")
    assert response.status_code == 400

def test_model_performance():
    response = client.get("/api/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert len(data["metrics"]) > 0
    
    perf = data["metrics"][0]
    assert "model" in perf
    assert "mae" in perf
    assert "rmse" in perf
    assert "rank" in perf

if __name__ == "__main__":
    # If run directly, run pytest on this file
    import pytest
    sys.exit(pytest.main([__file__]))
