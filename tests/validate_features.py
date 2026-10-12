import os
import pandas as pd

def validate_monthly_features():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed/beds_monthly_features.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    
    # Check shape
    assert len(df) == 64, f"Expected 64 rows for monthly features, got {len(df)}"
    # Check no nulls
    nulls = df.isnull().sum().sum()
    assert nulls == 0, f"Found {nulls} NaN values in monthly features!"
    
    # Check key columns
    expected_cols = [
        'g_and_a_beds_occupied_lag_1', 'g_and_a_beds_occupied_lag_12',
        'g_and_a_beds_occupied_rolling_mean_3', 'month', 'quarter'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in monthly features!"
        
    print("Monthly Beds features: VALIDATED (Passed all checks).")

def validate_icu_features():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed/icu_daily_features.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    
    assert len(df) == 152, f"Expected 152 rows for ICU daily features, got {len(df)}"
    nulls = df.isnull().sum().sum()
    assert nulls == 0, f"Found {nulls} NaN values in ICU daily features!"
    
    expected_cols = [
        'occupied_beds_lag_1', 'occupied_beds_lag_28',
        'occupied_beds_rolling_mean_7', 'day_of_week', 'is_weekend'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in ICU daily features!"
        
    print("ICU Daily features: VALIDATED (Passed all checks).")

def validate_ed_features():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed/ed_daily_features.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    
    assert len(df) == 152, f"Expected 152 rows for ED daily features, got {len(df)}"
    nulls = df.isnull().sum().sum()
    assert nulls == 0, f"Found {nulls} NaN values in ED daily features!"
    
    expected_cols = [
        'arrivals_lag_1', 'arrivals_lag_28',
        'arrivals_rolling_mean_7', 'day_of_week', 'is_weekend'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Expected column {col} not found in ED daily features!"
        
    print("ED Daily features: VALIDATED (Passed all checks).")

if __name__ == "__main__":
    print("--- Starting Feature Datasets Validation ---")
    validate_monthly_features()
    validate_icu_features()
    validate_ed_features()
    print("All feature datasets are correct and ready for model training!")
