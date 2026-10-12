import os
import io
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set testing flag in env
os.environ["TESTING"] = "True"

from backend.main import app
from backend.database import Base, get_db
from backend.models.db_models import User, Dataset, DataEntry, Forecast, Alert, Recommendation, HistoricalDemand
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

def test_pipeline_invalid_user_rejection():
    # Viewer tries to trigger forecasting (forbidden)
    headers = get_auth_headers("viewer", "ViewerPassword123")
    response = client.post(
        "/api/data/forecast/generate",
        json={"dataset_id": 1, "model": "XGBoost", "retrain": False},
        headers=headers
    )
    assert response.status_code == 403

def test_pipeline_generate_valid():
    headers = get_auth_headers("planner", "PlannerPassword123")
    
    # 1. Create a Dataset batch
    from backend.database import SessionLocal
    db = SessionLocal()
    planner_user = db.query(User).filter_by(username="planner").first()
    
    db_dataset = Dataset(
        filename="test_upload.csv",
        source_type="CSV_UPLOAD",
        uploaded_by=planner_user.id,
        row_count=1,
        validation_status="VALIDATED",
        processing_status="STORED"
    )
    db.add(db_dataset)
    db.commit()
    db_dataset_id = db_dataset.id
    
    # 2. Add a manual observation data entry
    target_date = date.today() - timedelta(days=2)
    db.add(DataEntry(
        date=target_date,
        resource="ICU Demand",
        value=15.0,
        source_type="UPLOADED_DATASET",
        created_by=planner_user.id,
        dataset_id=db_dataset_id
    ))
    db.commit()
    db.close()

    # 3. Planner triggers forecast generation
    response = client.post(
        "/api/data/forecast/generate",
        json={"dataset_id": db_dataset_id, "model": "XGBoost", "retrain": False},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "PROCESSED"
    assert data["dataset_id"] == db_dataset_id
    assert data["selected_model"] == "XGBoost"

    # Check database records
    db = SessionLocal()
    forecasts = db.query(Forecast).filter_by(dataset_id=db_dataset_id).all()
    assert len(forecasts) > 0
    assert forecasts[0].model == "XGBoost"
    
    # Check that alerts and recommendations were generated
    alerts = db.query(Alert).filter(Alert.predicted_demand > 0).all()
    assert len(alerts) > 0
    recs = db.query(Recommendation).all()
    assert len(recs) > 0
    db.close()

def test_pipeline_admin_retrain():
    # Admin can trigger model retraining
    headers = get_auth_headers("admin", "AdminPassword123")
    response = client.post(
        "/api/data/forecast/generate",
        json={"dataset_id": 1, "model": "XGBoost", "retrain": True},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "training_range" in response.json()

def test_pipeline_insufficient_data_rejection():
    # Attempting forecast on database where historical records are cleared
    headers = get_auth_headers("admin", "AdminPassword123")
    
    # Create database session, clear historical demand
    from backend.database import SessionLocal
    db = SessionLocal()
    db.query(HistoricalDemand).delete()
    db.commit()
    db.close()

    response = client.post(
        "/api/data/forecast/generate",
        json={"dataset_id": 1, "model": "XGBoost", "retrain": False},
        headers=headers
    )
    assert response.status_code == 400
    assert "Insufficient historical data" in response.json()["detail"]
