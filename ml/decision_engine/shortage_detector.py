import os
import pandas as pd
import numpy as np
import thresholds

def validate_inputs(df, expected_rows=7):
    """
    Validates that the prediction dataframe meets structural and value constraints.
    """
    if len(df) != expected_rows:
        raise ValueError(f"Forecast horizon must be exactly {expected_rows} days, got {len(df)}.")
        
    if df['date'].duplicated().any():
        raise ValueError("Forecast dates contain duplicate entries.")
        
    if not pd.api.types.is_numeric_dtype(df['predicted']):
        raise ValueError("Predicted demand values must be numeric.")
        
    if (df['predicted'] < 0).any():
        raise ValueError("Predicted demand contains invalid negative values.")

def detect_icu_shortages(forecast_path):
    """
    Computes capacity gaps and risk alerts for ICU beds.
    """
    if not os.path.exists(forecast_path):
        raise FileNotFoundError(f"ICU forecast file not found at: {forecast_path}")
        
    df = pd.read_csv(forecast_path)
    validate_inputs(df)
    
    capacity = thresholds.ICU_CAPACITY
    if capacity is None or not isinstance(capacity, (int, float)) or capacity < 0:
        raise ValueError("Capacity data unavailable or invalid.")
        
    records = []
    for _, row in df.iterrows():
        pred = float(row['predicted'])
        gap = float(capacity - pred)
        occ_rate = pred / capacity if capacity > 0 else 0
        
        # Risk level determination
        if pred > capacity:
            risk = "HIGH"
            reason = f"Predicted demand ({pred:.2f} beds) exceeds available capacity of {capacity:.1f} beds."
        elif pred >= capacity * thresholds.ICU_MEDIUM_PCT:
            risk = "MEDIUM"
            reason = f"Predicted demand ({pred:.2f} beds) is approaching capacity limit ({occ_rate*100:.1f}% occupied)."
        else:
            risk = "LOW"
            reason = "Predicted demand is within safe capacity bounds."
            
        records.append({
            'date': row['date'],
            'resource': 'ICU Beds',
            'predicted_demand': pred,
            'available_capacity': capacity,
            'capacity_gap': gap,
            'risk_level': risk,
            'reason': reason
        })
        
    return pd.DataFrame(records)

def detect_ed_pressure(forecast_path):
    """
    Computes demand pressure levels for ED arrivals.
    Note: ED arrivals are a demand metric and not a direct measure of physical bed capacity.
    """
    if not os.path.exists(forecast_path):
        raise FileNotFoundError(f"ED forecast file not found at: {forecast_path}")
        
    df = pd.read_csv(forecast_path)
    validate_inputs(df)
    
    baseline = thresholds.ED_BASELINE
    if baseline is None or not isinstance(baseline, (int, float)) or baseline < 0:
        raise ValueError("ED baseline data unavailable or invalid.")
        
    records = []
    for _, row in df.iterrows():
        pred = float(row['predicted'])
        # In ED, available capacity is simulated as the historical baseline
        gap = float(baseline - pred)
        
        # Pressure determination
        if pred > baseline * thresholds.ED_THRESHOLD_MULT:
            risk = "HIGH"
            pct_above = ((pred - baseline) / baseline) * 100
            reason = f"ED arrivals predicted at {pred:.2f} patients, which is {pct_above:.1f}% above baseline."
        elif pred >= baseline:
            risk = "MEDIUM"
            reason = f"ED arrivals predicted at {pred:.2f} patients, slightly exceeding baseline of {baseline:.1f}."
        else:
            risk = "LOW"
            reason = "ED arrivals predicted within standard baseline variation."
            
        records.append({
            'date': row['date'],
            'resource': 'ED Arrivals',
            'predicted_demand': pred,
            'available_capacity': baseline,
            'capacity_gap': gap,
            'risk_level': risk,
            'reason': reason
        })
        
    return pd.DataFrame(records)

def run_shortage_detection():
    interim_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/interim"
    alerts_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/alerts"
    
    icu_forecast = os.path.join(interim_dir, "xgboost_icu_forecast.csv")
    ed_forecast = os.path.join(interim_dir, "xgboost_ed_forecast.csv")
    
    print("\nRunning shortage detection...")
    
    df_icu = detect_icu_shortages(icu_forecast)
    df_ed = detect_ed_pressure(ed_forecast)
    
    df_all = pd.concat([df_icu, df_ed], ignore_index=True)
    
    os.makedirs(alerts_dir, exist_ok=True)
    alerts_csv = os.path.join(alerts_dir, "resource_alerts.csv")
    df_all.to_csv(alerts_csv, index=False)
    
    print(f"Generated {len(df_all)} resource alerts. Saved to: {alerts_csv}")
    print("\nSample Alerts Summary:")
    print(df_all[['date', 'resource', 'predicted_demand', 'available_capacity', 'capacity_gap', 'risk_level']])

if __name__ == "__main__":
    run_shortage_detection()
