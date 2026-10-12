import os
import pandas as pd
import numpy as np
import xgboost as xgb
import shap

def run_shap_explainer(input_path, global_out_path, local_out_path, target_col, forecast_horizon=7):
    """
    Fits the XGBoost model on train features, computes SHAP global and local values,
    and saves them in structured CSV formats.
    """
    print(f"\nComputing SHAP for: {input_path}")
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Features and target
    feature_cols = [col for col in df.columns if col not in ['date', target_col]]
    
    train_df = df.iloc[:-forecast_horizon].copy()
    test_df = df.iloc[-forecast_horizon:].copy()
    
    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    
    # Train model (deterministic)
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Initialize KernelExplainer (model-agnostic, avoids XGBoost 3.x/2.x serialization bugs)
    # We use a summary dataset of 30 samples for background references to run quickly
    background_data = shap.sample(X_train, 30, random_state=42)
    explainer = shap.KernelExplainer(lambda x: model.predict(x), background_data)
    shap_values = explainer.shap_values(X_train)
    
    # 1. Global Importance: Mean absolute SHAP values per feature
    # shap_values has shape (N_samples, N_features)
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    
    df_global = pd.DataFrame({
        'feature': feature_cols,
        'shap_mean_abs': mean_abs_shap
    }).sort_values(by='shap_mean_abs', ascending=False)
    
    os.makedirs(os.path.dirname(global_out_path), exist_ok=True)
    df_global.to_csv(global_out_path, index=False)
    print(f"  Saved global SHAP values to: {global_out_path}")
    
    # 2. Local Explanation: Explain the final day prediction of the test window (index -1 in X_test)
    local_instance = X_test.iloc[[-1]] # 2D shape (1, N_features)
    local_shap = explainer.shap_values(local_instance)
    
    # shap_values for single instance
    contributions = local_shap[0]
    feature_values = local_instance.iloc[0].values
    
    df_local = pd.DataFrame({
        'feature': feature_cols,
        'value': feature_values,
        'contribution': contributions,
        'direction': np.where(contributions >= 0, 1, -1)
    })
    
    # Sort by absolute contribution descending
    df_local = df_local.iloc[df_local['contribution'].abs().argsort()[::-1]].reset_index(drop=True)
    
    os.makedirs(os.path.dirname(local_out_path), exist_ok=True)
    df_local.to_csv(local_out_path, index=False)
    print(f"  Saved local SHAP explanation to: {local_out_path}")

if __name__ == "__main__":
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    out_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/explainability/shap"
    
    run_shap_explainer(
        os.path.join(proc_dir, "icu_daily_features.csv"),
        os.path.join(out_dir, "icu_global.csv"),
        os.path.join(out_dir, "icu_local.csv"),
        target_col='occupied_beds'
    )
    
    run_shap_explainer(
        os.path.join(proc_dir, "ed_daily_features.csv"),
        os.path.join(out_dir, "ed_global.csv"),
        os.path.join(out_dir, "ed_local.csv"),
        target_col='arrivals'
    )
