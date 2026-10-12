import os
import json
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

def safe_mape(y_true, y_pred):
    """
    Computes MAPE safely, ignoring cases where y_true is 0.
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    non_zero = y_true != 0
    if not np.any(non_zero):
        return 0.0
    return np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero]))

def run_prophet_forecast(input_path, output_path, target_col, forecast_horizon=7):
    """
    Trains a Prophet model on daily data and forecasts the last forecast_horizon days.
    Saves predictions and returns metrics.
    """
    print(f"\nRunning Prophet for: {input_path}")
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Format for Prophet: ds and y
    prophet_df = df.rename(columns={'date': 'ds', target_col: 'y'})[['ds', 'y']]
    
    # Chronological Split
    train_df = prophet_df.iloc[:-forecast_horizon].copy()
    test_df = prophet_df.iloc[-forecast_horizon:].copy()
    
    # Initialize Prophet (180 days is too short for yearly seasonality, but weekly is vital)
    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False
    )
    
    # Fit model
    model.fit(train_df)
    
    # Predict future (which is the test set period)
    future = model.make_future_dataframe(periods=forecast_horizon)
    forecast = model.predict(future)
    
    # Extract predicted values for test window
    predictions = forecast.iloc[-forecast_horizon:][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    predictions = predictions.rename(columns={
        'ds': 'date',
        'yhat': 'predicted',
        'yhat_lower': 'lower_bound',
        'yhat_upper': 'upper_bound'
    })
    
    # Merge with actuals
    predictions['actual'] = test_df['y'].values
    
    # Calculate metrics
    y_true = predictions['actual']
    y_pred = predictions['predicted']
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = safe_mape(y_true, y_pred)
    
    print(f"  Metrics - MAE: {mae:.4f}, RMSE: {rmse:.4f}, MAPE: {mape:.4f}")
    
    # Save predictions
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    predictions.to_csv(output_path, index=False)
    print(f"  Saved predictions to: {output_path}")
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape
    }

if __name__ == "__main__":
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    interim_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/interim"
    metrics_path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/forecasting/prophet/metrics.json"
    
    icu_metrics = run_prophet_forecast(
        os.path.join(proc_dir, "icu_daily_processed.csv"),
        os.path.join(interim_dir, "prophet_icu_forecast.csv"),
        target_col='occupied_beds'
    )
    
    ed_metrics = run_prophet_forecast(
        os.path.join(proc_dir, "ed_daily_processed.csv"),
        os.path.join(interim_dir, "prophet_ed_forecast.csv"),
        target_col='arrivals'
    )
    
    metrics = {
        'icu': icu_metrics,
        'ed': ed_metrics
    }
    
    # Save metrics JSON
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"\nSaved metrics to: {metrics_path}")
