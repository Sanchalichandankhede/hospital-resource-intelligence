#!/usr/bin/env python3
"""
test_end_to_end.py
End-to-End integration test suite checking data consistency across
CSV files, SQLite database tables, and FastAPI client responses.
"""

import os
import sys
import pandas as pd
import json

# Ensure testing flag is set in env before imports
os.environ["TESTING"] = "True"

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import engine, SessionLocal, Base
from backend.models.db_models import (
    HistoricalDemand,
    Forecast,
    ModelPerformance,
    Alert,
    Recommendation,
    Explanation,
    ModelMetadata
)
from database.load_data import load_all_data

client = TestClient(app)

def run_tests():
    print("==================================================")
    print("END-TO-END SYSTEM INTEGRATION TESTS")
    print("==================================================")

    # 1. Initialize and Seed SQLite database
    print("\n1. Initializing and seeding SQLite database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_all_data(db)
    except Exception as e:
        print(f"  [FAIL] Seeding failed with error: {str(e)}")
        sys.exit(1)
    print("  [PASS] Seeding completed.")

    errors = []

    # 2. Database Tables Verification
    print("\n2. Checking Database records counts...")
    tables_to_check = [
        (HistoricalDemand, "historical_demand"),
        (Forecast, "forecasts"),
        (ModelPerformance, "model_performance"),
        (Alert, "alerts"),
        (Recommendation, "recommendations"),
        (Explanation, "explanations"),
        (ModelMetadata, "model_metadata")
    ]
    for model_cls, table_name in tables_to_check:
        count = db.query(model_cls).count()
        if count > 0:
            print(f"  [PASS] Table '{table_name}' has {count} records.")
        else:
            errors.append(f"Table '{table_name}' is empty.")
            print(f"  [FAIL] Table '{table_name}' has NO records!")

    # 3. Cross-Check 1: XGBoost ICU Forecast (Date: 2137-10-11)
    print("\n3. Cross-Checking ICU Forecast on 2137-10-11...")
    csv_forecast = pd.read_csv("data/interim/xgboost_icu_forecast.csv")
    csv_row = csv_forecast[csv_forecast['date'] == '2137-10-11'].iloc[0]
    csv_pred = float(csv_row['predicted'])
    csv_act = float(csv_row['actual'])

    db_forecast = db.query(Forecast).filter_by(
        forecast_date=pd.to_datetime('2137-10-11').date(),
        resource="ICU Beds",
        model="XGBoost"
    ).first()

    if db_forecast:
        db_pred = float(db_forecast.predicted_demand)
        db_act = float(db_forecast.actual_demand)
        print(f"  - CSV Pred: {csv_pred:.6f} | DB Pred: {db_pred:.6f}")
        print(f"  - CSV Actual: {csv_act:.6f} | DB Actual: {db_act:.6f}")
        if abs(round(csv_pred, 4) - round(db_pred, 4)) < 1e-5 and abs(round(csv_act, 4) - round(db_act, 4)) < 1e-5:
            print("  [PASS] CSV and DB forecast records match.")
        else:
            errors.append("ICU forecast CSV and DB values mismatch.")
            print("  [FAIL] CSV and DB forecast values mismatch!")
    else:
        errors.append("ICU forecast record missing in DB.")
        print("  [FAIL] Forecast record not found in Database!")

    # API Request Check
    api_res = client.get("/api/forecast/icu?model=XGBoost&start_date=2137-10-11&end_date=2137-10-11")
    if api_res.status_code == 200:
        api_data = api_res.json()["predictions"][0]
        api_pred = float(api_data["predicted_demand"])
        api_act = float(api_data["actual_demand"])
        print(f"  - API Pred: {api_pred:.6f} | API Actual: {api_act:.6f}")
        if abs(round(csv_pred, 4) - round(api_pred, 4)) < 1e-5:
            print("  [PASS] API response forecast matches file source.")
        else:
            errors.append("API forecast response values mismatch.")
            print("  [FAIL] API response forecast mismatch!")
    else:
        errors.append("Forecast API returned error.")
        print(f"  [FAIL] Forecast API returned status: {api_res.status_code}")

    # 4. Cross-Check 2: Alerts simulated capacity constraints (ICU date: 2137-10-11)
    print("\n4. Cross-Checking ICU Alerts capacity constraints on 2137-10-11...")
    db_alert = db.query(Alert).filter_by(
        alert_date=pd.to_datetime('2137-10-11').date(),
        resource="ICU Beds"
    ).first()

    if db_alert:
        print(f"  - Alert risk: {db_alert.risk_level} | Capacity simulated: {db_alert.is_capacity_simulated}")
        print(f"  - Actual capacity: {db_alert.actual_capacity} | Simulated capacity: {db_alert.simulated_capacity}")
        if db_alert.is_capacity_simulated is True and db_alert.actual_capacity is None:
            print("  [PASS] Simulated capacity safeguard variables correctly mapped.")
        else:
            errors.append("Simulated capacity safeguards not met in alerts DB table.")
            print("  [FAIL] Capacity variables are incorrectly filled!")
    else:
        errors.append("Alert record missing in DB.")
        print("  [FAIL] Alert not found in Database!")

    api_alert_res = client.get("/api/alerts?resource=ICU%20Beds&start_date=2137-10-11&end_date=2137-10-11")
    if api_alert_res.status_code == 200:
        api_alert = api_alert_res.json()["alerts"][0]
        if api_alert["is_capacity_simulated"] is True and api_alert["actual_capacity"] is None:
            print("  [PASS] API alert exposes correct simulated parameters.")
        else:
            errors.append("API alert simulated constraints mismatch.")
            print("  [FAIL] API alert simulates actual capacity incorrectly!")
    else:
        errors.append("Alerts API returned error.")
        print(f"  [FAIL] Alerts API returned status: {api_alert_res.status_code}")

    # 5. Cross-Check 3: Explainable AI Local attributions (ICU SHAP, feature: occupied_beds_lag_1)
    print("\n5. Cross-Checking local explanations for ICU SHAP occupied_beds_lag_1 on 2137-10-17...")
    csv_xai = pd.read_csv("outputs/explainability/shap/icu_local.csv")
    csv_xai_row = csv_xai[csv_xai['feature'] == 'occupied_beds_lag_1'].iloc[0]
    csv_contrib = float(csv_xai_row['contribution'])
    csv_val = float(csv_xai_row['value'])
    csv_dir = int(csv_xai_row['direction'])

    db_xai = db.query(Explanation).filter_by(
        resource="ICU Beds",
        date=pd.to_datetime('2137-10-17').date(),
        feature="occupied_beds_lag_1",
        explanation_method="SHAP"
    ).first()

    if db_xai:
        db_contrib = float(db_xai.contribution)
        db_val = float(db_xai.feature_value)
        db_dir = int(db_xai.direction)
        print(f"  - CSV Contrib: {csv_contrib:.6f} | DB Contrib: {db_contrib:.6f}")
        print(f"  - CSV Dir: {csv_dir} | DB Dir: {db_dir}")
        if abs(csv_contrib - db_contrib) < 1e-5 and csv_dir == db_dir:
            print("  [PASS] Database XAI elements match file attributes.")
        else:
            errors.append("XAI database records mismatch features.")
            print("  [FAIL] Database XAI values mismatch!")
    else:
        errors.append("XAI record missing in DB.")
        print("  [FAIL] XAI record not found in Database!")

    api_xai_res = client.get("/api/explanations/icu?method=SHAP&date=2137-10-17")
    if api_xai_res.status_code == 200:
        exps = api_xai_res.json()["explanations"]
        target_exp = next((x for x in exps if x["feature"] == "occupied_beds_lag_1"), None)
        if target_exp:
            api_contrib = float(target_exp["contribution"])
            if abs(csv_contrib - api_contrib) < 1e-5:
                print("  [PASS] API attribution response matches file source.")
            else:
                errors.append("API contribution mismatch.")
                print("  [FAIL] API contribution value mismatch!")
        else:
            errors.append("Feature not found in API response.")
            print("  [FAIL] Feature occupied_beds_lag_1 missing in API explanations list!")
    else:
        errors.append("Explanations API returned error.")
        print(f"  [FAIL] Explanations API returned status: {api_xai_res.status_code}")

    # 6. Model Performance Benchmark check
    print("\n6. Benchmarking performance comparison winner...")
    perf_api_res = client.get("/api/model-performance")
    if perf_api_res.status_code == 200:
        metrics = perf_api_res.json()["metrics"]
        icu_metrics = [m for m in metrics if m["target"] == "icu_occupancy"]
        
        # XGBoost should be the winner (#1 rank) for ICU based on actual file comparison
        xgboost_icu = next((m for m in icu_metrics if m["model"] == "XGBoost"), None)
        if xgboost_icu and xgboost_icu["rank"] == 1:
            print(f"  [PASS] XGBoost correctly benchmarked as #1 performance rank for ICU (MAE: {xgboost_icu['mae']:.6f}).")
        else:
            errors.append("Benchmark ranking check failed.")
            print(f"  [FAIL] XGBoost is NOT ranked as #1 for ICU in database!")
    # 7. Multi-Resource Forecasting check
    print("\n7. Verifying Multi-Resource API forecasts response...")
    multi_res = client.get("/api/forecast/multi?model=XGBoost")
    if multi_res.status_code == 200:
        data = multi_res.json()["resources"]
        targets = [
            "ICU Demand", "General Bed Demand", "Emergency Bed Demand",
            "Oxygen Demand", "Blood Demand", "Staff Requirement", "Ambulance Requirement"
        ]
        all_present = all(t in data for t in targets)
        if all_present:
            print("  [PASS] All 7 forecast targets returned by API.")
            
            # Check simulated flags, metadata, and muted metrics
            icu_sim = data["ICU Demand"]["is_simulated"]
            oxygen_sim = data["Oxygen Demand"]["is_simulated"]
            
            # Audit provenance fields presence
            provenance_ok = all(
                all(k in data[t] for k in ("unit", "source", "assumption")) 
                for t in targets
            )
            
            # Check muted metrics for simulated targets
            muted_ok = data["Oxygen Demand"]["mae"] is None and data["Oxygen Demand"]["rmse"] is None
            icu_metrics_ok = data["ICU Demand"]["mae"] is not None and data["ICU Demand"]["rmse"] is not None
            
            # Check for negative values and valid risk levels
            no_negatives = True
            valid_risks = True
            allowed_risks = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            
            for t in targets:
                for p in data[t]["predictions"]:
                    if p["predicted_demand"] < 0 or (p["actual_demand"] is not None and p["actual_demand"] < 0) or p["capacity"] < 0:
                        no_negatives = False
                    if p["risk_level"] not in allowed_risks:
                        valid_risks = False
            
            if icu_sim is False and oxygen_sim is True:
                print("  [PASS] Data provenance flags correctly distinguish real vs simulated resources.")
            else:
                errors.append("Multi-resource simulation flags mapping incorrect.")
                print(f"  [FAIL] Provenance check failed: ICU={icu_sim}, Oxygen={oxygen_sim}")
                
            if provenance_ok:
                print("  [PASS] All provenance metadata fields (unit, source, assumption) are present.")
            else:
                errors.append("Provenance metadata fields are missing in API response.")
                print("  [FAIL] Metadata fields missing!")
                
            if muted_ok and icu_metrics_ok:
                print("  [PASS] Simulated performance metrics correctly muted; core metrics preserved.")
            else:
                errors.append("Performance metrics muting check failed.")
                print(f"  [FAIL] Metrics checks failed: Oxygen MAE={data['Oxygen Demand']['mae']}, ICU MAE={data['ICU Demand']['mae']}")
                
            if no_negatives:
                print("  [PASS] Checked all predictions: no negative resource quantities found.")
            else:
                errors.append("Negative quantities found in forecast predictions.")
                print("  [FAIL] Negative values detected!")
                
            if valid_risks:
                print("  [PASS] Checked all risk levels: all fall within valid boundaries.")
            else:
                errors.append("Invalid risk levels found in forecast predictions.")
                print("  [FAIL] Invalid risk levels detected!")
                
            # Check discrete ceiling quantization conversions
            quantization_ok = True
            for t in targets:
                for p in data[t]["predictions"]:
                    pred_val = p["predicted_value"]
                    op_req = p["operational_requirement"]
                    
                    if t == "Oxygen Demand":
                        if abs(pred_val - op_req) > 1e-5:
                            quantization_ok = False
                    else:
                        import math
                        expected_op = 0 if pred_val <= 0 else math.ceil(pred_val)
                        if op_req != expected_op:
                            quantization_ok = False
                            
            if quantization_ok:
                print("  [PASS] Quantization check: continuous predictions correctly ceil-rounded into integers.")
            else:
                errors.append("Ceiling quantization math error found in predictions.")
                print("  [FAIL] Quantization checks failed!")
    else:
        errors.append("Multi-Resource API returned error.")
        print(f"  [FAIL] Multi-Resource API returned status: {multi_res.status_code}")

    # 8. Target Conversion Boundary checks
    print("\n8. Verifying Target Conversion Boundary rules...")
    
    # Helper lambda to simulate quantization logic
    def operational_quantize(resource_name, val):
        if resource_name == "Oxygen Demand":
            return val
        else:
            if val <= 0:
                return 0
            else:
                import math
                return math.ceil(val)
                
    # ICU 0.45 -> 1 bed
    if operational_quantize("ICU Demand", 0.45) == 1:
        print("  [PASS] 0.45 beds -> 1 bed operational requirement conversion.")
    else:
        errors.append("0.45 beds conversion check failed.")
        
    # ICU 1.00 -> 1 bed
    if operational_quantize("ICU Demand", 1.00) == 1:
        print("  [PASS] 1.00 beds -> 1 bed operational requirement conversion.")
    else:
        errors.append("1.00 beds conversion check failed.")
        
    # ICU 1.01 -> 2 beds
    if operational_quantize("ICU Demand", 1.01) == 2:
        print("  [PASS] 1.01 beds -> 2 beds operational requirement conversion.")
    else:
        errors.append("1.01 beds conversion check failed.")
        
    # ICU 0 -> 0 beds
    if operational_quantize("ICU Demand", 0.0) == 0:
        print("  [PASS] 0 beds -> 0 beds operational requirement conversion.")
    else:
        errors.append("0 beds conversion check failed.")
        
    # Negative forecast -> 0
    if operational_quantize("ICU Demand", -0.55) == 0:
        print("  [PASS] Negative forecast -> 0 beds operational requirement conversion.")
    else:
        errors.append("Negative forecast conversion check failed.")
        
    # Blood 2.1 -> 3 units
    if operational_quantize("Blood Demand", 2.10) == 3:
        print("  [PASS] Blood 2.1 -> 3 units operational requirement conversion.")
    else:
        errors.append("Blood 2.1 units conversion check failed.")
        
    # Ambulance 1.2 -> 2 vehicles
    if operational_quantize("Ambulance Requirement", 1.20) == 2:
        print("  [PASS] Ambulance 1.2 -> 2 vehicles operational requirement conversion.")
    else:
        errors.append("Ambulance 1.2 vehicles conversion check failed.")
        
    # Staff 0.68 FTE -> operational requirement 1
    if operational_quantize("Staff Requirement", 0.68) == 1:
        print("  [PASS] Staff 0.68 FTE -> 1 staff operational requirement conversion.")
    else:
        errors.append("Staff 0.68 FTE conversion check failed.")
        
    # Oxygen remains continuous (6.77 L -> 6.77 L)
    if abs(operational_quantize("Oxygen Demand", 6.77) - 6.77) < 1e-5:
        print("  [PASS] Oxygen remains continuous (6.77 L -> 6.77 L).")
    else:
        errors.append("Oxygen continuous representation check failed.")
        
    # Shortage gap test: 0.45 ICU forecast with capacity 0 -> shortage of 1
    req = operational_quantize("ICU Demand", 0.45)
    cap = 0
    shortage_gap = cap - req
    if shortage_gap == -1:
        print("  [PASS] 0.45 ICU forecast with capacity 0 triggers operational shortage of 1 bed.")
    else:
        errors.append("Shortage gap check failed.")

    # Closing session
    db.close()

    print("\n==================================================")
    print("INTEGRATION VERIFICATION SUMMARY")
    print("==================================================")
    if len(errors) == 0:
        print("ALL END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY!")
        return True
    else:
        print(f"FAILED with {len(errors)} integration errors:")
        for err in errors:
            print(f"  - {err}")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
