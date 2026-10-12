import os
import json
import pandas as pd

def validate_forecast(path, expected_rows=7):
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    
    # Check shape
    assert len(df) == expected_rows, f"Expected {expected_rows} rows, got {len(df)}"
    
    # Check column names
    expected_cols = ['date', 'actual', 'predicted', 'lower_bound', 'upper_bound']
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in forecast!"
        
    # Check no nulls
    assert df.isnull().sum().sum() == 0, f"Found NaN values in forecast {path}!"
    print(f"Prophet forecast at {os.path.basename(path)}: VALIDATED (Passed all checks).")

def validate_metrics():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/forecasting/prophet/metrics.json"
    assert os.path.exists(path), f"Metrics file {path} does not exist!"
    
    with open(path, 'r') as f:
        metrics = json.load(f)
        
    assert 'icu' in metrics, "Missing ICU metrics!"
    assert 'ed' in metrics, "Missing ED metrics!"
    
    for key in ['icu', 'ed']:
        for metric_name in ['mae', 'rmse', 'mape']:
            assert metric_name in metrics[key], f"Missing {metric_name} in {key} metrics!"
            assert isinstance(metrics[key][metric_name], (int, float)), f"{metric_name} is not a number!"
            
    print("Prophet performance metrics.json: VALIDATED (Passed all checks).")

if __name__ == "__main__":
    print("--- Starting Prophet Forecasting Validation ---")
    interim_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/interim"
    validate_forecast(os.path.join(interim_dir, "prophet_icu_forecast.csv"))
    validate_forecast(os.path.join(interim_dir, "prophet_ed_forecast.csv"))
    validate_metrics()
    print("Prophet forecasting stage outputs are validated successfully!")
