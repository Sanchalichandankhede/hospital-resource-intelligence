import os
import json
import numpy as np
import pandas as pd
from datetime import date, timedelta
from sqlalchemy.orm import Session

from backend.models.db_models import HistoricalDemand, Forecast, DataEntry, Dataset, Alert, Recommendation
from ml.features.generator import create_daily_features

PROJECT_ROOT = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence"

def generate_dynamic_forecast(db: Session, model_name: str, dataset_id: int, retrain: bool = False) -> dict:
    """
    Executes the dynamic data-to-forecast pipeline.
    1. Loads and merges historical baseline + user entries.
    2. Validates sequence size (minimum 30 days required).
    3. Runs model training/retraining or inference.
    4. Generates predictions for the next 7 days.
    5. Saves predictions to the forecasts database table.
    6. Updates dataset batch processing status.
    7. Updates Alerts and Recommendations tables.
    """
    print(f"Starting forecast generation pipeline for model: {model_name}, Dataset ID: {dataset_id}, Retrain: {retrain}")
    
    # 1. Fetch dataset batch details
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise ValueError(f"Dataset with ID {dataset_id} not found.")

    dataset.processing_status = "PROCESSING"
    db.commit()

    try:
        # 2. Load historical baseline
        hist_rows = db.query(HistoricalDemand).order_by(HistoricalDemand.date.asc()).all()
        
        # 3. Load user-provided entries
        entry_rows = db.query(DataEntry).order_by(DataEntry.date.asc()).all()

        # ICU Data merge: Map "ICU Demand" from entries to "ICU Beds"
        icu_baseline = {r.date: float(r.actual_demand) for r in hist_rows if r.resource == "ICU Beds"}
        for entry in entry_rows:
            if entry.resource == "ICU Demand":
                icu_baseline[entry.date] = float(entry.value)

        # ED Data merge: Map "Emergency Bed Demand" from entries to "ED Arrivals"
        ed_baseline = {r.date: float(r.actual_demand) for r in hist_rows if r.resource == "ED Arrivals"}
        for entry in entry_rows:
            if entry.resource == "Emergency Bed Demand":
                # Convert from Admission Beds (25%) back to daily arrivals count (1.0 / 0.25 = 4x)
                # This aligns with the conversion formula: Emergency Bed Demand = ED Arrivals * 0.25
                ed_baseline[entry.date] = float(entry.value) * 4.0

        # Construct Sorted Dataframes
        icu_hist_df = pd.DataFrame([{"date": k, "occupied_beds": v} for k, v in icu_baseline.items()], columns=["date", "occupied_beds"])
        icu_hist_df = icu_hist_df.sort_values("date").reset_index(drop=True)

        ed_hist_df = pd.DataFrame([{"date": k, "arrivals": v} for k, v in ed_baseline.items()], columns=["date", "arrivals"])
        ed_hist_df = ed_hist_df.sort_values("date").reset_index(drop=True)

        # 4. Small-data check: validation constraints (minimum 30 rows)
        if len(icu_hist_df) < 30 or len(ed_hist_df) < 30:
            dataset.processing_status = "FAILED"
            dataset.forecast_status = "FAILED"
            db.commit()
            return {
                "success": False,
                "status": "FAILED",
                "detail": "Insufficient historical data for reliable model retraining. Existing model/forecast remains unchanged."
            }

        # Determine forecasting horizon (7 days after the last historical date)
        last_date = max(icu_hist_df["date"].max(), ed_hist_df["date"].max())
        if isinstance(last_date, str):
            last_date = date.fromisoformat(last_date)
        
        future_dates = [last_date + timedelta(days=i) for i in range(1, 8)]

        # 5. Core Model Execution
        icu_forecasts = []
        ed_forecasts = []

        if model_name.upper() == "PROPHET":
            icu_forecasts = run_prophet(icu_hist_df, "occupied_beds", future_dates)
            ed_forecasts = run_prophet(ed_hist_df, "arrivals", future_dates)

        elif model_name.upper() == "XGBOOST":
            icu_forecasts = run_xgboost(icu_hist_df, "occupied_beds", future_dates, retrain)
            ed_forecasts = run_xgboost(ed_hist_df, "arrivals", future_dates, retrain)

        elif model_name.upper() == "LSTM":
            icu_forecasts = run_lstm(icu_hist_df, "occupied_beds", future_dates, "icu", retrain)
            ed_forecasts = run_lstm(ed_hist_df, "arrivals", future_dates, "ed", retrain)

        else:
            raise ValueError(f"Unknown forecasting model: {model_name}")

        # 6. Save new predictions to forecasts table
        # Delete old forecasts for these dates and model
        for f_date in future_dates:
            db.query(Forecast).filter(
                Forecast.forecast_date == f_date,
                Forecast.model == model_name
            ).delete()
        db.commit()

        # Insert new forecasts
        for f_date, val in icu_forecasts:
            db.add(Forecast(
                forecast_date=f_date,
                resource="ICU Beds",
                predicted_demand=val,
                actual_demand=None,
                model=model_name,
                forecast_horizon="7 days",
                dataset_id=dataset_id
            ))

        for f_date, val in ed_forecasts:
            db.add(Forecast(
                forecast_date=f_date,
                resource="ED Arrivals",
                predicted_demand=val,
                actual_demand=None,
                model=model_name,
                forecast_horizon="7 days",
                dataset_id=dataset_id
            ))
        db.commit()

        # Update dataset statuses
        dataset.processing_status = "PROCESSED"
        dataset.forecast_status = "FORECAST_GENERATED"
        db.commit()

        # 7. Update alerts & recommendations
        generate_decision_engine_records(db, model_name, future_dates, icu_forecasts, ed_forecasts)

        return {
            "success": True,
            "status": "PROCESSED",
            "detail": "Forecast generated successfully.",
            "selected_model": model_name,
            "training_range": f"{icu_hist_df['date'].min()} to {icu_hist_df['date'].max()}",
            "forecast_horizon": "7 days",
            "dataset_id": dataset_id
        }

    except Exception as e:
        db.rollback()
        if dataset:
            dataset.processing_status = "FAILED"
            dataset.forecast_status = "FAILED"
            db.commit()
        print(f"Error in forecast pipeline: {str(e)}")
        raise e

# --- Model Specific Helper Functions ---

def run_prophet(hist_df: pd.DataFrame, target_col: str, future_dates: list) -> list:
    """Trains a Prophet model and returns predictions."""
    from prophet import Prophet
    prophet_df = hist_df.rename(columns={"date": "ds", target_col: "y"})
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False
    )
    model.fit(prophet_df)

    future = pd.DataFrame({"ds": pd.to_datetime(future_dates)})
    forecast = model.predict(future)
    
    preds = np.clip(forecast["yhat"].values, 0.0, None)
    return [(d, float(p)) for d, p in zip(future_dates, preds)]


def run_xgboost(hist_df: pd.DataFrame, target_col: str, future_dates: list, retrain: bool) -> list:
    """Trains an XGBoost model autoregressively and returns predictions."""
    import xgboost as xgb
    hist_df = hist_df.copy()
    hist_df["date"] = pd.to_datetime(hist_df["date"])

    # Generate historical features to define column names
    temp_features = create_daily_features(hist_df, target_col)
    feature_cols = [col for col in temp_features.columns if col not in ["date", target_col]]

    # Train XGBoost
    X_train = temp_features[feature_cols]
    y_train = temp_features[target_col]

    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Autoregressive Prediction Loop
    current_df = hist_df.copy()
    predictions = []

    for next_date in future_dates:
        # Append empty row with 0.0 placeholder
        next_row = pd.DataFrame({"date": [pd.to_datetime(next_date)], target_col: [0.0]})
        extended_df = pd.concat([current_df, next_row], ignore_index=True)

        # Generate features
        features_df = create_daily_features(extended_df, target_col)
        last_row_features = features_df.iloc[-1:]

        X_pred = last_row_features[feature_cols]
        pred_val = float(model.predict(X_pred)[0])
        pred_val = max(0.0, pred_val)

        predictions.append((next_date, pred_val))

        # Update target value in current dataframe
        next_row_updated = pd.DataFrame({"date": [pd.to_datetime(next_date)], target_col: [pred_val]})
        current_df = pd.concat([current_df, next_row_updated], ignore_index=True)

    return predictions


def run_lstm(hist_df: pd.DataFrame, target_col: str, future_dates: list, model_name: str, retrain: bool) -> list:
    """Loads/trains PyTorch LSTM and returns predictions."""
    import torch
    from ml.forecasting.lstm.model import LSTMRegressor
    data = hist_df[target_col].values.astype(np.float32)
    seq_len = 7
    horizon = 7

    # Scale data
    # Fit scaler strictly on history
    scaler_input = data.reshape(-1, 1)
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    scaler.fit(scaler_input)

    # Instantiate model
    model = LSTMRegressor(
        input_size=1,
        hidden_size=16,
        num_layers=1,
        dropout=0.2,
        horizon=horizon
    )

    checkpoint_path = os.path.join(PROJECT_ROOT, f"ml/forecasting/lstm/checkpoints/best_{model_name}_lstm.pth")
    
    if os.path.exists(checkpoint_path) and not retrain:
        # Load weights
        model.load_state_dict(torch.load(checkpoint_path, map_location=torch.device('cpu')))
    else:
        # Mini training loop on history if retrain=True or checkpoint missing
        from torch.utils.data import TensorDataset, DataLoader
        import torch.optim as optim
        import torch.nn as nn
        
        scaled_data = scaler.transform(scaler_input).flatten()
        
        # Build sequences
        X_lst = []
        y_lst = []
        for i in range(len(scaled_data) - seq_len - horizon + 1):
            X_lst.append(scaled_data[i : i + seq_len])
            y_lst.append(scaled_data[i + seq_len : i + seq_len + horizon])
        
        X_np = np.array(X_lst)[..., np.newaxis]
        y_np = np.array(y_lst)
        
        X_t = torch.tensor(X_np, dtype=torch.float32)
        y_t = torch.tensor(y_np, dtype=torch.float32)
        
        train_loader = DataLoader(TensorDataset(X_t, y_t), batch_size=8, shuffle=False)
        
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        
        model.train()
        for epoch in range(30): # Quick retraining epochs
            for bx, by in train_loader:
                optimizer.zero_grad()
                loss = criterion(model(bx), by)
                loss.backward()
                optimizer.step()
                
    # Inference
    model.eval()
    last_seq = data[-seq_len:]
    last_seq_scaled = scaler.transform(last_seq.reshape(-1, 1)).flatten()
    input_t = torch.tensor(last_seq_scaled, dtype=torch.float32).view(1, seq_len, 1)

    with torch.no_grad():
        preds_scaled = model(input_t).numpy().flatten()

    preds_raw = scaler.inverse_transform(preds_scaled.reshape(-1, 1)).flatten()
    preds_raw = np.clip(preds_raw, 0.0, None)

    return [(d, float(p)) for d, p in zip(future_dates, preds_raw)]


def generate_decision_engine_records(db: Session, model_name: str, future_dates: list, icu_forecasts: list, ed_forecasts: list):
    """Generates Alert and Recommendation records in the database."""
    # Delete old alerts/recs for these dates
    for f_date in future_dates:
        # Delete recommendations linked to alerts first to avoid FK constraints
        db.query(Recommendation).filter(Recommendation.date == f_date).delete()
        db.query(Alert).filter(Alert.alert_date == f_date).delete()
    db.commit()

    # Alert Thresholds definitions (consistent with shortage_detector.py)
    ICU_CAPACITY = 2.0
    ED_BASELINE = 2.0

    # 1. Map ICU alerts
    for f_date, val in icu_forecasts:
        gap = ICU_CAPACITY - val
        if val > ICU_CAPACITY:
            risk = "HIGH"
            reason = f"Predicted demand ({val:.2f} beds) exceeds available capacity of {ICU_CAPACITY:.1f} beds."
        elif val >= ICU_CAPACITY * 0.90:
            risk = "MEDIUM"
            reason = f"Predicted demand ({val:.2f} beds) is approaching capacity limit."
        else:
            risk = "LOW"
            reason = "Predicted demand is within safe capacity bounds."

        db_alert = Alert(
            alert_date=f_date,
            resource="ICU Beds",
            predicted_demand=val,
            actual_capacity=None,
            simulated_capacity=ICU_CAPACITY,
            is_capacity_simulated=True,
            capacity_gap=gap,
            risk_level=risk,
            reason=reason
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)

        # Map corresponding Recommendation
        if risk == "LOW":
            rec_text = "Current predicted demand is within available capacity. Continue routine monitoring."
            trig_text = "Predicted demand matches safe operational thresholds."
        else:
            rec_text = "Predicted demand exceeds available capacity. Review bed allocation and activate appropriate capacity-management procedures."
            trig_text = f"ICU occupancy predicted to hit {val:.2f} beds."

        db.add(Recommendation(
            alert_id=db_alert.id,
            date=f_date,
            resource="ICU Beds",
            risk_level=risk,
            recommendation=rec_text,
            trigger=trig_text,
            model=model_name
        ))

    # 2. Map ED alerts
    for f_date, val in ed_forecasts:
        gap = ED_BASELINE - val
        if val > ED_BASELINE * 1.20:
            risk = "HIGH"
            reason = f"ED arrivals predicted at {val:.2f} patients, which is 20% above baseline."
        elif val >= ED_BASELINE:
            risk = "MEDIUM"
            reason = f"ED arrivals predicted at {val:.2f} patients, slightly exceeding baseline."
        else:
            risk = "LOW"
            reason = "ED arrivals predicted within standard baseline variation."

        db_alert = Alert(
            alert_date=f_date,
            resource="ED Arrivals",
            predicted_demand=val,
            actual_capacity=None,
            simulated_capacity=ED_BASELINE,
            is_capacity_simulated=True,
            capacity_gap=gap,
            risk_level=risk,
            reason=reason
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)

        # Map corresponding Recommendation
        if risk == "LOW":
            rec_text = "Current predicted demand is within available capacity. Continue routine monitoring."
            trig_text = "Predicted demand matches safe operational thresholds."
        else:
            rec_text = "Predicted demand exceeds baseline limits. Coordinate ED throughput and review backup admissions capacity."
            trig_text = f"ED arrivals predicted at {val:.2f} patients."

        db.add(Recommendation(
            alert_id=db_alert.id,
            date=f_date,
            resource="ED Arrivals",
            risk_level=risk,
            recommendation=rec_text,
            trigger=trig_text,
            model=model_name
        ))

    db.commit()
