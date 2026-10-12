import os
import pandas as pd

def validate_comparison():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/ml/evaluation/model_comparison.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    
    # Check shape: 6 rows (3 models * 2 targets)
    assert len(df) == 6, f"Expected 6 rows, got {len(df)}"
    
    # Check columns
    expected_cols = ['target', 'model', 'mae', 'rmse', 'mape', 'mae_rank', 'rmse_rank']
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in comparison!"
        
    # Check models and targets
    targets = df['target'].unique()
    assert 'icu_occupancy' in targets, "Missing icu_occupancy target!"
    assert 'ed_arrivals' in targets, "Missing ed_arrivals target!"
    
    models = df['model'].unique()
    assert 'Prophet' in models, "Missing Prophet model!"
    assert 'XGBoost' in models, "Missing XGBoost model!"
    assert 'LSTM' in models, "Missing LSTM model!"
    
    # Check rank values
    for target in targets:
        df_t = df[df['target'] == target]
        # Check mae_rank ranges from 1 to 3
        ranks = df_t['mae_rank'].tolist()
        assert set(ranks) == {1, 2, 3}, f"Ranks are invalid for target {target}: {ranks}"
        
    print("Model comparison CSV: VALIDATED (Passed all checks).")

if __name__ == "__main__":
    print("--- Starting Model Comparison Validation ---")
    validate_comparison()
    print("Model comparison validation passes successfully!")
