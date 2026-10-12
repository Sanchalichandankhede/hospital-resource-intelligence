import os
import pandas as pd

def validate_beds():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed/beds_monthly_processed.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Check shape
    assert len(df) == 76, f"Expected 76 rows, got {len(df)}"
    # Check date sorted
    assert df['date'].is_monotonic_increasing, "Beds data dates are not sorted!"
    # Check no nulls in targets
    assert df['g_and_a_beds_occupied'].isnull().sum() == 0, "Nulls found in g_and_a_beds_occupied!"
    assert df['adult_critical_care_beds_occupied'].isnull().sum() == 0, "Nulls found in adult_critical_care_beds_occupied!"
    
    # Check month increments consecutively (approx 30 days)
    diffs = df['date'].diff().dropna()
    # Monthly diffs should be 28, 29, 30, or 31 days
    assert all(d.days in [28, 29, 30, 31] for d in diffs), f"Beds data dates are not consecutive monthly! Diffs: {[d.days for d in diffs]}"
    print("Beds Monthly processed dataset: VALIDATED (Passed all checks).")

def validate_icu():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed/icu_daily_processed.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    
    assert len(df) == 180, f"Expected 180 rows, got {len(df)}"
    assert df['date'].is_monotonic_increasing, "ICU daily dates are not sorted!"
    assert df['occupied_beds'].isnull().sum() == 0, "Nulls found in occupied_beds!"
    
    # Check daily continuity (diffs should be exactly 1 day)
    diffs = df['date'].diff().dropna()
    assert all(d.days == 1 for d in diffs), "ICU daily dates are not consecutive daily!"
    print("ICU Daily processed dataset: VALIDATED (Passed all checks).")

def validate_ed():
    path = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed/ed_daily_processed.csv"
    assert os.path.exists(path), f"File {path} does not exist!"
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    
    assert len(df) == 180, f"Expected 180 rows, got {len(df)}"
    assert df['date'].is_monotonic_increasing, "ED daily dates are not sorted!"
    assert df['arrivals'].isnull().sum() == 0, "Nulls found in arrivals!"
    
    # Check daily continuity
    diffs = df['date'].diff().dropna()
    assert all(d.days == 1 for d in diffs), "ED daily dates are not consecutive daily!"
    print("ED Daily processed dataset: VALIDATED (Passed all checks).")

if __name__ == "__main__":
    print("--- Starting Processed Datasets Validation ---")
    validate_beds()
    validate_icu()
    validate_ed()
    print("All processed datasets are correct and continuous!")
