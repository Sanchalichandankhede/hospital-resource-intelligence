import os
import json
import pandas as pd
import numpy as np
import xgboost as xgb
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

def run_xgboost_forecast(input_path, output_path, target_col, forecast_horizon=7):
    """
    Trains an XGBoost model on historical lags/rolling features and predicts the last 7 days.
    """
    print(f"\nRunning XGBoost for: {input_path}")
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Define features (X) and target (y)
    feature_cols = [col for col in df.columns if col not in ['date', target_col]]
    
    # Chronological Train-Test Split
    train_df = df.iloc[:-forecast_horizon].copy()
    test_df = df.iloc[-forecast_horizon:].copy()
    
    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]
    
    # Train XGBRegressor
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Predict
    preds = model.predict(X_test)
    
    # Round predictions to nearest non-negative value since occupied beds / arrivals are integers
    # For time-series regression models, keeping float predictions is fine for metrics, 
    # but we can also clip them at 0.
    preds = np.clip(preds, 0, None)
    
    # Calculate metrics
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mape = safe_mape(y_test, preds)
    
    print(f"  Metrics - MAE: {mae:.4f}, RMSE: {rmse:.4f}, MAPE: {mape:.4f}")
    
    # Save predictions
    predictions_df = pd.DataFrame({
        'date': test_df['date'],
        'actual': y_test,
        'predicted': preds
    })
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    predictions_df.to_csv(output_path, index=False)
    print(f"  Saved predictions to: {output_path}")
    
    # Get feature importance
    importance = model.feature_importances_
    feat_importance = {feat: float(imp) for feat, imp in zip(feature_cols, importance)}
    
    return {
        'metrics': {
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        },
        'feature_importance': feat_importance
    }

if __name__ == "__main__":
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    interim_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/interim"
    metrics_path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/forecasting/xgboost/metrics.json"
    feat_imp_path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/forecasting/xgboost/feature_importance.json"
    
    icu_results = run_xgboost_forecast(
        os.path.join(proc_dir, "icu_daily_features.csv"),
        os.path.join(interim_dir, "xgboost_icu_forecast.csv"),
        target_col='occupied_beds'
    )
    
    ed_results = run_xgboost_forecast(
        os.path.join(proc_dir, "ed_daily_features.csv"),
        os.path.join(interim_dir, "xgboost_ed_forecast.csv"),
        target_col='arrivals'
    )
    
    metrics = {
        'icu': icu_results['metrics'],
        'ed': ed_results['metrics']
    }
    
    feature_importances = {
        'icu': icu_results['feature_importance'],
        'ed': ed_results['feature_importance']
    }
    
    # Save metrics JSON
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"Saved metrics to: {metrics_path}")
    
    # Save Feature Importance JSON
    with open(feat_imp_path, 'w') as f:
        json.dump(feature_importances, f, indent=4)
    print(f"Saved feature importances to: {feat_imp_path}")
