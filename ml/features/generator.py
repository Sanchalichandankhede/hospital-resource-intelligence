import pandas as pd
import numpy as np

def create_daily_features(df, target_col, lags=[1, 2, 3, 7, 14, 28], rolling_windows=[7, 14, 28]):
    """
    Generates historical, rolling, and calendar features for daily time-series.
    Shifts the series before computing rolling windows to prevent data leakage.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # 1. Historical Lags
    for lag in lags:
        df[f"{target_col}_lag_{lag}"] = df[target_col].shift(lag)
        
    # 2. Rolling Statistics (Shifted by 1 to prevent data leakage of the current day)
    for window in rolling_windows:
        df[f"{target_col}_rolling_mean_{window}"] = df[target_col].shift(1).rolling(window).mean()
        df[f"{target_col}_rolling_std_{window}"] = df[target_col].shift(1).rolling(window).std()
        
    # 3. Calendar Features
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6]).astype(int)
    
    # Drop rows with NaN (due to lags and rolling stats)
    df = df.dropna().reset_index(drop=True)
    return df

def create_monthly_features(df, target_cols, lags=[1, 2, 12], rolling_windows=[3, 6]):
    """
    Generates features for monthly time-series.
    """
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # 1. Lags & Rolling Stats for each target
    for target_col in target_cols:
        for lag in lags:
            df[f"{target_col}_lag_{lag}"] = df[target_col].shift(lag)
        for window in rolling_windows:
            df[f"{target_col}_rolling_mean_{window}"] = df[target_col].shift(1).rolling(window).mean()
            
    # 2. Calendar Features
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    
    # Drop rows with NaN
    df = df.dropna().reset_index(drop=True)
    return df

if __name__ == "__main__":
    # Test feature generator if invoked directly
    import os
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    
    # Test Beds monthly
    beds_path = os.path.join(proc_dir, "beds_monthly_processed.csv")
    if os.path.exists(beds_path):
        df_beds = pd.read_csv(beds_path)
        df_beds_feats = create_monthly_features(
            df_beds, 
            ['g_and_a_beds_occupied', 'adult_critical_care_beds_occupied'],
            lags=[1, 2, 12],
            rolling_windows=[3, 6]
        )
        df_beds_feats.to_csv(os.path.join(proc_dir, "beds_monthly_features.csv"), index=False)
        print(f"Generated monthly features: {df_beds_feats.shape}")
        
    # Test ICU Daily
    icu_path = os.path.join(proc_dir, "icu_daily_processed.csv")
    if os.path.exists(icu_path):
        df_icu = pd.read_csv(icu_path)
        df_icu_feats = create_daily_features(df_icu, 'occupied_beds')
        df_icu_feats.to_csv(os.path.join(proc_dir, "icu_daily_features.csv"), index=False)
        print(f"Generated ICU daily features: {df_icu_feats.shape}")
        
    # Test ED Daily
    ed_path = os.path.join(proc_dir, "ed_daily_processed.csv")
    if os.path.exists(ed_path):
        df_ed = pd.read_csv(ed_path)
        df_ed_feats = create_daily_features(df_ed, 'arrivals')
        df_ed_feats.to_csv(os.path.join(proc_dir, "ed_daily_features.csv"), index=False)
        print(f"Generated ED daily features: {df_ed_feats.shape}")
