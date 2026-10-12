import os
import json
import pandas as pd
from datetime import date
from sqlalchemy.orm import Session
from backend.database import engine, Base, SessionLocal
from backend.models.db_models import (
    HistoricalDemand,
    Forecast,
    ModelPerformance,
    Alert,
    Recommendation,
    Explanation,
    ModelMetadata,
    User,
    Dataset
)

PROJECT_ROOT = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence"

def parse_date(date_val):
    if pd.isna(date_val):
        return None
    if isinstance(date_val, (date, pd.Timestamp)):
        return date_val.date() if hasattr(date_val, 'date') else date_val
    return date.fromisoformat(str(date_val).split()[0])

def load_all_data(db: Session):
    print("Initializing Database tables...")
    # Safe initialization: creates tables if they don't exist, does not delete existing data.
    Base.metadata.create_all(bind=engine)
    
    # 0. Seed Default Users
    print("\n0. Seeding Default Users...")
    from passlib.context import CryptContext
    from backend.config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    default_users = [
        {"username": DEFAULT_ADMIN_USERNAME, "email": DEFAULT_ADMIN_EMAIL, "password": DEFAULT_ADMIN_PASSWORD, "role": "ADMIN"},
        {"username": "planner", "email": "planner@example.com", "password": "PlannerPassword123", "role": "PLANNER"},
        {"username": "viewer", "email": "viewer@example.com", "password": "ViewerPassword123", "role": "VIEWER"}
    ]
    
    for u in default_users:
        existing = db.query(User).filter_by(username=u["username"]).first()
        if not existing:
            db.add(User(
                username=u["username"],
                email=u["email"],
                password_hash=pwd_context.hash(u["password"]),
                role=u["role"],
                is_active=True
            ))
    db.commit()
    print("  - Seeded default accounts.")
    
    # 1. Seed Default Dataset tracking batch
    print("\n1. Seeding Default Dataset tracking batch...")
    default_dataset = db.query(Dataset).filter_by(source_type="EXISTING_DATA").first()
    if not default_dataset:
        default_dataset = Dataset(
            filename="historical_demand_baseline",
            source_type="EXISTING_DATA",
            resource_type="Multi-Resource",
            row_count=360,
            validation_status="VALIDATED",
            processing_status="PROCESSED",
            forecast_status="FORECAST_GENERATED"
        )
        db.add(default_dataset)
        db.commit()
        db.refresh(default_dataset)
    default_dataset_id = default_dataset.id
    print("  - Seeded default dataset tracking batch.")

    # 1.5. Seed Historical Demand
    print("\n1.5. Seeding Historical Demand...")
    icu_hist_path = os.path.join(PROJECT_ROOT, "data/processed/icu_daily_processed.csv")
    ed_hist_path = os.path.join(PROJECT_ROOT, "data/processed/ed_daily_processed.csv")
    
    if os.path.exists(icu_hist_path):
        df = pd.read_csv(icu_hist_path)
        for _, row in df.iterrows():
            d = parse_date(row['date'])
            val = float(row['occupied_beds'])
            if val < 0:
                continue  # skip negative counts
            existing = db.query(HistoricalDemand).filter_by(date=d, resource="ICU Beds").first()
            if not existing:
                db.add(HistoricalDemand(date=d, resource="ICU Beds", actual_demand=val, target_type="occupancy"))
        print("  - Mapped ICU daily historical demand.")

    if os.path.exists(ed_hist_path):
        df = pd.read_csv(ed_hist_path)
        for _, row in df.iterrows():
            d = parse_date(row['date'])
            val = float(row['arrivals'])
            if val < 0:
                continue
            existing = db.query(HistoricalDemand).filter_by(date=d, resource="ED Arrivals").first()
            if not existing:
                db.add(HistoricalDemand(date=d, resource="ED Arrivals", actual_demand=val, target_type="arrivals"))
        print("  - Mapped ED daily historical demand.")
    db.commit()

    # 2. Seed Forecasts
    print("\n2. Seeding Model Forecasts...")
    forecast_files = {
        ("icu_daily_processed.csv", "ICU Beds", "Prophet", "prophet_icu_forecast.csv"),
        ("icu_daily_processed.csv", "ICU Beds", "XGBoost", "xgboost_icu_forecast.csv"),
        ("icu_daily_processed.csv", "ICU Beds", "LSTM", "lstm_icu_forecast.csv"),
        ("ed_daily_processed.csv", "ED Arrivals", "Prophet", "prophet_ed_forecast.csv"),
        ("ed_daily_processed.csv", "ED Arrivals", "XGBoost", "xgboost_ed_forecast.csv"),
        ("ed_daily_processed.csv", "ED Arrivals", "LSTM", "lstm_ed_forecast.csv"),
    }
    
    for _, resource, model, filename in forecast_files:
        path = os.path.join(PROJECT_ROOT, "data/interim", filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                d = parse_date(row['date'])
                pred = float(row['predicted'])
                act = float(row['actual']) if 'actual' in row and not pd.isna(row['actual']) else None
                
                existing = db.query(Forecast).filter_by(forecast_date=d, resource=resource, model=model).first()
                if not existing:
                    db.add(Forecast(
                        forecast_date=d,
                        resource=resource,
                        predicted_demand=pred,
                        actual_demand=act,
                        model=model,
                        forecast_horizon="7 days",
                        dataset_id=default_dataset_id
                    ))
            print(f"  - Mapped forecast from: {filename}")
    db.commit()

    # 3. Seed Model Performance Metrics
    print("\n3. Seeding Model Comparison Performance metrics...")
    comparison_path = os.path.join(PROJECT_ROOT, "ml/evaluation/model_comparison.csv")
    if os.path.exists(comparison_path):
        df = pd.read_csv(comparison_path)
        for _, row in df.iterrows():
            target_str = "icu_occupancy" if "icu" in str(row['target']).lower() else "ed_arrivals"
            model = row['model']
            mae = float(row['mae'])
            rmse = float(row['rmse'])
            mape = float(row['mape']) if 'mape' in row and not pd.isna(row['mape']) else None
            rank = int(row['mae_rank'])
            
            existing = db.query(ModelPerformance).filter_by(model=model, target=target_str).first()
            if not existing:
                db.add(ModelPerformance(
                    model=model,
                    target=target_str,
                    mae=mae,
                    rmse=rmse,
                    mape=mape,
                    evaluation_period="Holdout Evaluation Horizon (7 days)",
                    rank=rank
                ))
        print("  - Mapped model evaluation metrics.")
    db.commit()

    # 4. Seed Alerts
    print("\n4. Seeding Decision Engine Shortage Alerts...")
    alerts_path = os.path.join(PROJECT_ROOT, "outputs/alerts/resource_alerts.csv")
    if os.path.exists(alerts_path):
        df = pd.read_csv(alerts_path)
        for _, row in df.iterrows():
            d = parse_date(row['date'])
            res = row['resource']
            pred = float(row['predicted_demand'])
            sim_cap = float(row['available_capacity'])
            gap = float(row['capacity_gap'])
            risk = row['risk_level']
            reason = row['reason']
            
            existing = db.query(Alert).filter_by(alert_date=d, resource=res).first()
            if not existing:
                db.add(Alert(
                    alert_date=d,
                    resource=res,
                    predicted_demand=pred,
                    actual_capacity=None,  # Null as per schema limitation
                    simulated_capacity=sim_cap,
                    is_capacity_simulated=True,  # Explicit flag indicating simulated bounds
                    capacity_gap=gap,
                    risk_level=risk,
                    reason=reason
                ))
        print("  - Mapped resource alerts.")
    db.commit()

    # 5. Seed Recommendations
    print("\n5. Seeding Operational Recommendations...")
    recs_path = os.path.join(PROJECT_ROOT, "outputs/recommendations/recommendations.csv")
    if os.path.exists(recs_path):
        df = pd.read_csv(recs_path)
        for _, row in df.iterrows():
            d = parse_date(row['date'])
            res = row['resource']
            risk = row['risk_level']
            rec = row['recommendation']
            trig = row['trigger']
            model = row['model']
            
            # Fetch corresponding alert to maintain foreign key link
            alert = db.query(Alert).filter_by(alert_date=d, resource=res).first()
            alert_id = alert.id if alert else None
            
            existing = db.query(Recommendation).filter_by(date=d, resource=res).first()
            if not existing:
                db.add(Recommendation(
                    alert_id=alert_id,
                    date=d,
                    resource=res,
                    risk_level=risk,
                    recommendation=rec,
                    trigger=trig,
                    model=model
                ))
        print("  - Mapped recommendations (foreign keys established).")
    db.commit()

    # 6. Seed XAI Local Explanations
    print("\n6. Seeding Local XAI Explanations (SHAP & LIME)...")
    explanation_files = [
        ("ICU Beds", "2137-10-17", "SHAP", "outputs/explainability/shap/icu_local.csv"),
        ("ED Arrivals", "2148-01-25", "SHAP", "outputs/explainability/shap/ed_local.csv"),
        ("ICU Beds", "2137-10-17", "LIME", "outputs/explainability/lime/icu_local.csv"),
        ("ED Arrivals", "2148-01-25", "LIME", "outputs/explainability/lime/ed_local.csv"),
    ]
    
    for resource, date_str, method, rel_path in explanation_files:
        path = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(path):
            d = parse_date(date_str)
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                feat = row['feature']
                val = float(row['value'])
                contrib = float(row['contribution'])
                dir_val = int(row['direction'])
                
                existing = db.query(Explanation).filter_by(
                    resource=resource, date=d, model="XGBoost", feature=feat, explanation_method=method
                ).first()
                if not existing:
                    db.add(Explanation(
                        resource=resource,
                        date=d,
                        model="XGBoost",
                        feature=feat,
                        feature_value=val,
                        contribution=contrib,
                        direction=dir_val,
                        explanation_method=method
                    ))
            print(f"  - Mapped {method} explanations for: {resource}")
    db.commit()

    # 7. Seed Model Metadata (Global Importance & Loss logs)
    print("\n7. Seeding Global Model Importance and Loss History Metadata...")
    
    # Global SHAP
    global_shaps = [
        ("icu_occupancy", "outputs/explainability/shap/icu_global.csv"),
        ("ed_arrivals", "outputs/explainability/shap/ed_global.csv"),
    ]
    for target, rel_path in global_shaps:
        path = os.path.join(PROJECT_ROOT, rel_path)
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                feat = row['feature']
                val = float(row['shap_mean_abs'])
                
                existing = db.query(ModelMetadata).filter_by(
                    model="XGBoost", target=target, metadata_type="global_shap_importance", feature=feat
                ).first()
                if not existing:
                    db.add(ModelMetadata(
                        model="XGBoost",
                        target=target,
                        metadata_type="global_shap_importance",
                        feature=feat,
                        value=val
                    ))
            print(f"  - Mapped global SHAP feature importance for target: {target}")

    # XGBoost internal importances
    xgb_imp_path = os.path.join(PROJECT_ROOT, "ml/forecasting/xgboost/feature_importance.json")
    if os.path.exists(xgb_imp_path):
        with open(xgb_imp_path, "r") as f:
            data = json.load(f)
        for target, feat_dict in data.items():
            target_str = "icu_occupancy" if target == "icu" else "ed_arrivals"
            for feat, val in feat_dict.items():
                existing = db.query(ModelMetadata).filter_by(
                    model="XGBoost", target=target_str, metadata_type="internal_feature_importance", feature=feat
                ).first()
                if not existing:
                    db.add(ModelMetadata(
                        model="XGBoost",
                        target=target_str,
                        metadata_type="internal_feature_importance",
                        feature=feat,
                        value=float(val)
                    ))
        print("  - Mapped internal XGBoost feature importances.")

    # LSTM loss history
    lstm_loss_path = os.path.join(PROJECT_ROOT, "ml/forecasting/lstm/loss_history.json")
    if os.path.exists(lstm_loss_path):
        with open(lstm_loss_path, "r") as f:
            loss_data = json.load(f)
        existing = db.query(ModelMetadata).filter_by(
            model="LSTM", target="icu_occupancy", metadata_type="loss_history", feature="icu"
        ).first()
        if not existing:
            db.add(ModelMetadata(
                model="LSTM",
                target="icu_occupancy",
                metadata_type="loss_history",
                feature="icu",
                json_data=loss_data
            ))
        print("  - Mapped LSTM training loss profile.")

    db.commit()
    print("\n==================================================")
    print("DATA SEEDING COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        load_all_data(db)
    finally:
        db.close()
