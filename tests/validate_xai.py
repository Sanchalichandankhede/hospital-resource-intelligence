import os
import pandas as pd

def validate_global_csv(path):
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    expected_cols = ['feature', 'shap_mean_abs']
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in global CSV!"
    assert df.isnull().sum().sum() == 0, f"Found NaN values in global CSV {path}!"
    assert pd.api.types.is_numeric_dtype(df['shap_mean_abs']), f"shap_mean_abs is not numeric in {path}!"
    print(f"XAI global file at {os.path.basename(path)}: VALIDATED (Passed all checks).")

def validate_local_csv(path):
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    expected_cols = ['feature', 'value', 'contribution', 'direction']
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in local CSV!"
    assert df.isnull().sum().sum() == 0, f"Found NaN values in local CSV {path}!"
    assert pd.api.types.is_numeric_dtype(df['value']), f"value is not numeric in {path}!"
    assert pd.api.types.is_numeric_dtype(df['contribution']), f"contribution is not numeric in {path}!"
    assert pd.api.types.is_numeric_dtype(df['direction']), f"direction is not numeric in {path}!"
    assert set(df['direction'].unique()).issubset({1, -1}), f"direction values must be in [1, -1], got {df['direction'].unique()} in {path}!"
    print(f"XAI local file at {os.path.basename(path)}: VALIDATED (Passed all checks).")

if __name__ == "__main__":
    print("--- Starting Explainable AI Validation ---")
    xai_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/explainability"
    
    validate_global_csv(os.path.join(xai_dir, "shap/icu_global.csv"))
    validate_global_csv(os.path.join(xai_dir, "shap/ed_global.csv"))
    
    validate_local_csv(os.path.join(xai_dir, "shap/icu_local.csv"))
    validate_local_csv(os.path.join(xai_dir, "shap/ed_local.csv"))
    
    validate_local_csv(os.path.join(xai_dir, "lime/icu_local.csv"))
    validate_local_csv(os.path.join(xai_dir, "lime/ed_local.csv"))
    
    print("XAI stage outputs are validated successfully!")
