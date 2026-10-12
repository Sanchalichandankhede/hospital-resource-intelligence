import os
import json
import pandas as pd
import numpy as np
import xgboost as xgb
from lime.lime_tabular import LimeTabularExplainer

def run_lime_explainer(input_path, local_out_path, target_col, forecast_horizon=7):
    """
    Fits the XGBoost model, initializes LIME Tabular Explainer,
    explains the final test day prediction locally, and saves the weights.
    """
    print(f"\nComputing LIME for: {input_path}")
    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    feature_cols = [col for col in df.columns if col not in ['date', target_col]]
    
    train_df = df.iloc[:-forecast_horizon].copy()
    test_df = df.iloc[-forecast_horizon:].copy()
    
    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    
    # Train model
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Initialize LIME Tabular Explainer
    explainer = LimeTabularExplainer(
        training_data=X_train.values,
        feature_names=feature_cols,
        class_names=[target_col],
        mode='regression',
        random_state=42
    )
    
    # Explain final instance of test window
    local_instance = X_test.iloc[-1]
    exp = explainer.explain_instance(
        data_row=local_instance.values,
        predict_fn=model.predict,
        num_features=len(feature_cols)
    )
    
    # Get local explanation weights
    # exp.local_exp is a dict where key is output index, value is list of (feature_idx, weight)
    key = list(exp.local_exp.keys())[0]
    local_weights = exp.local_exp[key]
    
    # Sort or map back to feature names
    records = []
    for feat_idx, weight in local_weights:
        records.append({
            'feature': feature_cols[feat_idx],
            'value': float(local_instance.values[feat_idx]),
            'contribution': float(weight),
            'direction': int(1 if weight >= 0 else -1)
        })
        
    df_local = pd.DataFrame(records)
    # Sort by absolute contribution descending
    df_local = df_local.iloc[df_local['contribution'].abs().argsort()[::-1]].reset_index(drop=True)
    
    os.makedirs(os.path.dirname(local_out_path), exist_ok=True)
    df_local.to_csv(local_out_path, index=False)
    print(f"  Saved local LIME values to: {local_out_path}")

if __name__ == "__main__":
    proc_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/data/processed"
    out_dir = "/Users/sanchalichandankhede/Documents/Idea lab/hospital-resource-intelligence/outputs/explainability/lime"
    
    run_lime_explainer(
        os.path.join(proc_dir, "icu_daily_features.csv"),
        os.path.join(out_dir, "icu_local.csv"),
        target_col='occupied_beds'
    )
    
    run_lime_explainer(
        os.path.join(proc_dir, "ed_daily_features.csv"),
        os.path.join(out_dir, "ed_local.csv"),
        target_col='arrivals'
    )
