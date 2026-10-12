import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict, Any, List, Optional
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.linear_model import Ridge
import xgboost as xgb

import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.forecasting.california_capacity_experiment import (
    build_training_features,
    run_recursive_forecast,
    safe_mape,
    DEFAULT_DATA_PATH
)

ROLLING_OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs", "rolling_evaluation")


def compute_mase(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    in_sample_seasonal_scale: float
) -> float:
    """
    Computes Mean Absolute Scaled Error (MASE) (Hyndman & Koehler, 2006).
    
    The scaling denominator is strictly computed in-sample on the training set:
        Q_train = (1 / (n - m)) * sum_{t=m+1}^n |y_t - y_{t-m}|
    where m=7 is the weekly seasonal lag.
    """
    if in_sample_seasonal_scale <= 0:
        return np.nan
    mae = float(mean_absolute_error(y_true, y_pred))
    return float(mae / in_sample_seasonal_scale)


def compute_in_sample_scale(y_train: np.ndarray, seasonal_period: int = 7) -> float:
    """
    Computes the in-sample mean absolute error of the one-step seasonal naive forecast
    using ONLY training data:
        Q_train = (1 / (n - m)) * sum_{t=m+1}^n |y_t - y_{t-m}|
    """
    y_train = np.asarray(y_train, dtype=float)
    if len(y_train) <= seasonal_period:
        raise ValueError(f"Training sequence length ({len(y_train)}) must be greater than seasonal period ({seasonal_period}).")
    abs_seasonal_diff = np.abs(y_train[seasonal_period:] - y_train[:-seasonal_period])
    return float(np.mean(abs_seasonal_diff))


def generate_rolling_origins(
    df: pd.DataFrame,
    horizon: int = 7,
    step: int = 7,
    num_origins: int = 52
) -> List[int]:
    """
    Generates cutoff indices for rolling origin evaluation:
    - Each origin k uses observations up to index cutoff_idx for training.
    - Test period for origin k is index cutoff_idx + 1 through cutoff_idx + horizon.
    - Spaced by 'step' days (default 7 days = weekly non-overlapping test windows).
    - With num_origins = 52, covers a full 52-week year (364 evaluated test days).
    """
    n_records = len(df)
    # The last origin test set ends exactly at the final record (index n_records - 1)
    last_cutoff_idx = n_records - 1 - horizon
    first_cutoff_idx = last_cutoff_idx - (num_origins - 1) * step

    if first_cutoff_idx < horizon + 30:
        raise ValueError(
            f"Requested {num_origins} origins with step {step} requires starting at index {first_cutoff_idx}, "
            f"which leaves insufficient training warm-up in dataset of length {n_records}."
        )

    cutoff_indices = [first_cutoff_idx + i * step for i in range(num_origins)]
    return cutoff_indices


def run_rolling_origin_evaluation(
    data_path: str = DEFAULT_DATA_PATH,
    target_col: str = "inpatient_beds_used",
    capacity_col: str = "inpatient_beds",
    horizon: int = 7,
    step: int = 7,
    num_origins: int = 52,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Executes a multi-origin chronological evaluation over repeated 7-day horizons.
    
    Leakage prevention:
    1. At origin k (cutoff date T_k), training uses only data available up to T_k.
    2. MASE scaling denominator Q_train is computed strictly on train data up to T_k.
    3. Capacity C_t is omitted from predictive features; C_{T_k} is recorded for context only.
    4. Multi-step ML predictions are generated genuinely recursively without querying ground truth.
    5. Baseline and ML models are evaluated on identical dates and horizons.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Processed dataset not found at: {data_path}")

    df_raw = pd.read_csv(data_path)
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_sorted = df_raw.sort_values("date").reset_index(drop=True)

    # Use continuous daily reporting (from 2020-03-01 onwards)
    ca_cont = df_sorted[df_sorted["date"] >= "2020-03-01"].reset_index(drop=True)

    cutoff_indices = generate_rolling_origins(
        ca_cont,
        horizon=horizon,
        step=step,
        num_origins=num_origins
    )

    all_predictions_records = []
    per_origin_metrics_records = []

    print(f"Starting rolling-origin evaluation over {num_origins} origins (Horizon = {horizon} days, Step = {step} days)...")

    for origin_idx, cutoff_idx in enumerate(cutoff_indices, start=1):
        train_df = ca_cont.iloc[:cutoff_idx + 1].copy()
        test_df = ca_cont.iloc[cutoff_idx + 1:cutoff_idx + 1 + horizon].copy()

        cutoff_date = train_df["date"].iloc[-1]
        test_start_date = test_df["date"].iloc[0]
        test_end_date = test_df["date"].iloc[-1]
        capacity_at_cutoff = float(train_df[capacity_col].iloc[-1])

        y_train = train_df[target_col].values.astype(float)
        y_test = test_df[target_col].values.astype(float)

        # 1. Training-only in-sample seasonal naive scale for MASE
        q_train = compute_in_sample_scale(y_train, seasonal_period=7)

        # 2. Weekly Seasonal Naive forecast: y_{T+h} = y_{T+h-7}
        # For horizon <= 7, all lag-7 values reside in train_df
        snaive_history = list(y_train)
        snaive_preds = []
        for _ in range(horizon):
            pred_sn = snaive_history[-7]
            snaive_preds.append(pred_sn)
            snaive_history.append(pred_sn)
        snaive_preds = np.array(snaive_preds)

        # 3. Train ML Models strictly on train_df
        train_feats_df, feature_cols = build_training_features(train_df, target_col=target_col)
        X_train = train_feats_df[feature_cols]
        y_train_clean = train_feats_df["y"].values

        # Ridge Regression
        ridge_model = Ridge(alpha=10.0, random_state=random_state)
        ridge_model.fit(X_train, y_train_clean)

        # XGBoost Regressor
        xgb_model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            random_state=random_state
        )
        xgb_model.fit(X_train, y_train_clean)

        # 4. Generate Recursive Multi-Step Predictions
        history_y = list(y_train)
        ridge_preds = run_recursive_forecast(
            model=ridge_model,
            history_y=history_y,
            last_known_date=cutoff_date,
            horizon_days=horizon,
            feature_cols=feature_cols
        )

        xgb_preds = run_recursive_forecast(
            model=xgb_model,
            history_y=history_y,
            last_known_date=cutoff_date,
            horizon_days=horizon,
            feature_cols=feature_cols
        )

        # 5. Record point-by-point predictions for each horizon step
        for h_step in range(1, horizon + 1):
            eval_date = test_df["date"].iloc[h_step - 1]
            act_val = float(y_test[h_step - 1])
            sn_val = float(snaive_preds[h_step - 1])
            rd_val = float(ridge_preds[h_step - 1])
            xg_val = float(xgb_preds[h_step - 1])

            all_predictions_records.append({
                "origin_id": origin_idx,
                "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
                "forecast_horizon_step": h_step,
                "target_date": eval_date.strftime("%Y-%m-%d"),
                "actual": act_val,
                "snaive_pred": sn_val,
                "snaive_err": act_val - sn_val,
                "snaive_abs_err": abs(act_val - sn_val),
                "ridge_pred": rd_val,
                "ridge_err": act_val - rd_val,
                "ridge_abs_err": abs(act_val - rd_val),
                "xgb_pred": xg_val,
                "xgb_err": act_val - xg_val,
                "xgb_abs_err": abs(act_val - xg_val),
                "q_train_scale": q_train,
                "capacity_at_cutoff": capacity_at_cutoff
            })

        # Origin-level summary metrics
        per_origin_metrics_records.append({
            "origin_id": origin_idx,
            "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
            "test_start_date": test_start_date.strftime("%Y-%m-%d"),
            "test_end_date": test_end_date.strftime("%Y-%m-%d"),
            "train_sample_size": len(train_df),
            "q_train_scale": round(q_train, 2),
            "capacity_at_cutoff": round(capacity_at_cutoff, 1),
            "snaive_mae": round(float(mean_absolute_error(y_test, snaive_preds)), 2),
            "snaive_rmse": round(float(np.sqrt(mean_squared_error(y_test, snaive_preds))), 2),
            "snaive_mase": round(float(mean_absolute_error(y_test, snaive_preds) / q_train), 4),
            "ridge_mae": round(float(mean_absolute_error(y_test, ridge_preds)), 2),
            "ridge_rmse": round(float(np.sqrt(mean_squared_error(y_test, ridge_preds))), 2),
            "ridge_mase": round(float(mean_absolute_error(y_test, ridge_preds) / q_train), 4),
            "xgb_mae": round(float(mean_absolute_error(y_test, xgb_preds)), 2),
            "xgb_rmse": round(float(np.sqrt(mean_squared_error(y_test, xgb_preds))), 2),
            "xgb_mase": round(float(mean_absolute_error(y_test, xgb_preds) / q_train), 4)
        })

    df_preds = pd.DataFrame(all_predictions_records)
    df_origins = pd.DataFrame(per_origin_metrics_records)

    # 6. Compute Horizon-Specific Metrics (h = 1..7)
    horizon_metrics_list = []
    for h in range(1, horizon + 1):
        df_h = df_preds[df_preds["forecast_horizon_step"] == h]
        y_true_h = df_h["actual"].values

        sn_pred_h = df_h["snaive_pred"].values
        rd_pred_h = df_h["ridge_pred"].values
        xg_pred_h = df_h["xgb_pred"].values

        # Mean scaled error across origins for step h
        sn_mase_h = float(np.mean(df_h["snaive_abs_err"] / df_h["q_train_scale"]))
        rd_mase_h = float(np.mean(df_h["ridge_abs_err"] / df_h["q_train_scale"]))
        xg_mase_h = float(np.mean(df_h["xgb_abs_err"] / df_h["q_train_scale"]))

        horizon_metrics_list.append({
            "horizon_step": h,
            "sample_count": len(df_h),
            "snaive_mae": round(float(mean_absolute_error(y_true_h, sn_pred_h)), 2),
            "snaive_rmse": round(float(np.sqrt(mean_squared_error(y_true_h, sn_pred_h))), 2),
            "snaive_mape": round(float(safe_mape(y_true_h, sn_pred_h)), 2),
            "snaive_mase": round(sn_mase_h, 4),
            "ridge_mae": round(float(mean_absolute_error(y_true_h, rd_pred_h)), 2),
            "ridge_rmse": round(float(np.sqrt(mean_squared_error(y_true_h, rd_pred_h))), 2),
            "ridge_mape": round(float(safe_mape(y_true_h, rd_pred_h)), 2),
            "ridge_mase": round(rd_mase_h, 4),
            "xgb_mae": round(float(mean_absolute_error(y_true_h, xg_pred_h)), 2),
            "xgb_rmse": round(float(np.sqrt(mean_squared_error(y_true_h, xg_pred_h))), 2),
            "xgb_mape": round(float(safe_mape(y_true_h, xg_pred_h)), 2),
            "xgb_mase": round(xg_mase_h, 4)
        })
    df_horizons = pd.DataFrame(horizon_metrics_list)

    # 7. Aggregate Overall Metrics (across all 364 evaluated points)
    y_true_all = df_preds["actual"].values
    total_eval_points = len(df_preds)

    def calc_overall(pred_col: str, abs_err_col: str) -> Dict[str, float]:
        preds_all = df_preds[pred_col].values
        mae = float(mean_absolute_error(y_true_all, preds_all))
        rmse = float(np.sqrt(mean_squared_error(y_true_all, preds_all)))
        mape = float(safe_mape(y_true_all, preds_all))
        mase = float(np.mean(df_preds[abs_err_col] / df_preds["q_train_scale"]))
        return {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mape": round(mape, 2),
            "mase": round(mase, 4)
        }

    overall_snaive = calc_overall("snaive_pred", "snaive_abs_err")
    overall_ridge = calc_overall("ridge_pred", "ridge_abs_err")
    overall_xgb = calc_overall("xgb_pred", "xgb_abs_err")

    summary_results = {
        "evaluation_name": "California Statewide Inpatient Beds Rolling-Origin Experiment",
        "dataset_path": data_path,
        "target": target_col,
        "parameters": {
            "num_origins": num_origins,
            "horizon_days": horizon,
            "step_days": step,
            "total_evaluated_observations_per_model": total_eval_points,
            "evaluation_start_date": df_origins["test_start_date"].iloc[0],
            "evaluation_end_date": df_origins["test_end_date"].iloc[-1],
            "first_cutoff_date": df_origins["cutoff_date"].iloc[0],
            "last_cutoff_date": df_origins["cutoff_date"].iloc[-1]
        },
        "overall_metrics": {
            "weekly_seasonal_naive": {
                "model_name": "Weekly Seasonal Naive (Lag-7 Persistence)",
                **overall_snaive
            },
            "ridge_regression_recursive": {
                "model_name": "Ridge Regression (Recursive Autoregressive)",
                **overall_ridge
            },
            "xgboost_recursive": {
                "model_name": "XGBoost Regressor (Recursive Autoregressive)",
                **overall_xgb
            }
        },
        "horizon_breakdown": horizon_metrics_list,
        "capacity_assumptions": {
            "contemporaneous_capacity_known_in_advance": False,
            "treatment": (
                "Total capacity (inpatient_beds) is contemporaneous telemetry and was excluded from feature inputs. "
                "At each forecast origin T_k, cutoff capacity C_{T_k} was recorded solely as an operational anchor."
            )
        }
    }

    return {
        "summary": summary_results,
        "predictions_df": df_preds,
        "origins_df": df_origins,
        "horizons_df": df_horizons
    }


def save_rolling_experiment_artifacts(
    results: Dict[str, Any],
    output_dir: str = ROLLING_OUTPUTS_DIR
) -> Dict[str, str]:
    """
    Persists all rolling origin evaluation artifacts to outputs/rolling_evaluation/:
    1. rolling_experiment_metrics.json
    2. rolling_forecast_predictions.csv
    3. rolling_horizon_metrics.csv
    4. rolling_origin_summary.csv
    5. rolling_horizon_comparison.png (Plot across horizons 1-7)
    6. ROLLING_ORIGIN_EXPERIMENT_REPORT.md
    """
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "rolling_experiment_metrics.json")
    preds_path = os.path.join(output_dir, "rolling_forecast_predictions.csv")
    horizons_path = os.path.join(output_dir, "rolling_horizon_metrics.csv")
    origins_path = os.path.join(output_dir, "rolling_origin_summary.csv")
    plot_path = os.path.join(output_dir, "rolling_horizon_comparison.png")
    report_path = os.path.join(output_dir, "ROLLING_ORIGIN_EXPERIMENT_REPORT.md")

    # 1. Save JSON metrics
    with open(json_path, "w") as f:
        json.dump(results["summary"], f, indent=2)

    # 2. Save CSVs
    results["predictions_df"].to_csv(preds_path, index=False)
    results["horizons_df"].to_csv(horizons_path, index=False)
    results["origins_df"].to_csv(origins_path, index=False)

    # 3. Generate Plot comparing performance across horizons 1..7
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), dpi=300)
    df_h = results["horizons_df"]
    h_steps = df_h["horizon_step"]

    # MAE across horizons
    ax1.plot(h_steps, df_h["snaive_mae"], "o-", label="Weekly Seasonal Naive", color="#0284c7", linewidth=2)
    ax1.plot(h_steps, df_h["ridge_mae"], "s-", label="Ridge Regression (Recursive)", color="#16a34a", linewidth=2)
    ax1.plot(h_steps, df_h["xgb_mae"], "^-", label="XGBoost (Recursive)", color="#dc2626", linewidth=2)
    ax1.set_title("Mean Absolute Error (MAE) by Forecast Horizon (h = 1..7)", fontsize=11, fontweight="bold", pad=10)
    ax1.set_xlabel("Forecast Horizon Step (Days)", fontsize=10)
    ax1.set_ylabel("MAE (Inpatient Beds Used)", fontsize=10)
    ax1.set_xticks(h_steps)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(frameon=True, facecolor="white")

    # MASE across horizons
    ax2.plot(h_steps, df_h["snaive_mase"], "o-", label="Weekly Seasonal Naive", color="#0284c7", linewidth=2)
    ax2.plot(h_steps, df_h["ridge_mase"], "s-", label="Ridge Regression (Recursive)", color="#16a34a", linewidth=2)
    ax2.plot(h_steps, df_h["xgb_mase"], "^-", label="XGBoost (Recursive)", color="#dc2626", linewidth=2)
    ax2.axhline(1.0, color="#64748b", linestyle=":", label="In-Sample Baseline (MASE = 1.0)")
    ax2.set_title("Mean Absolute Scaled Error (MASE) by Forecast Horizon", fontsize=11, fontweight="bold", pad=10)
    ax2.set_xlabel("Forecast Horizon Step (Days)", fontsize=10)
    ax2.set_ylabel("MASE (Scaled Error)", fontsize=10)
    ax2.set_xticks(h_steps)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(frameon=True, facecolor="white")

    plt.tight_layout()
    fig.savefig(plot_path, dpi=300)
    plt.close(fig)

    # 4. Generate Markdown Report
    summary = results["summary"]
    p = summary["parameters"]
    ov = summary["overall_metrics"]

    report_content = f"""# California Inpatient Capacity: 52-Week Rolling-Origin Evaluation Report

## 1. Executive Summary
This report documents the rigorous, rolling-origin evaluation of daily inpatient bed demand (`inpatient_beds_used`) across **{p['num_origins']} weekly forecast origins** spanning **{p['evaluation_start_date']} through {p['evaluation_end_date']}** ({p['total_evaluated_observations_per_model']} evaluated forecast days per model).

To ensure academic and operational rigor:
1. Every forecast origin uses strictly historical training data prior to that cutoff.
2. In-sample seasonal naive scale ($Q_{{train}}$) for MASE is computed strictly on training data at each origin.
3. Multi-step forecasts for Ridge and XGBoost are generated **recursively** without accessing future ground truth.
4. Total capacity is omitted from predictive features to prevent contemporaneous capacity leakage.

---

## 2. Overall Aggregate Model Performance
Evaluated across **{p['total_evaluated_observations_per_model']} paired observations** (52 origins $\\times$ 7 days):

| Model Architecture | Multi-Step Strategy | MAE (Beds) | RMSE (Beds) | MAPE (%) | MASE |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Weekly Seasonal Naive** | Lag-7 Persistence | **{ov['weekly_seasonal_naive']['mae']:.2f}** | **{ov['weekly_seasonal_naive']['rmse']:.2f}** | **{ov['weekly_seasonal_naive']['mape']:.2f}%** | **{ov['weekly_seasonal_naive']['mase']:.4f}** |
| **Ridge Regression** | Recursive Autoregressive | **{ov['ridge_regression_recursive']['mae']:.2f}** | **{ov['ridge_regression_recursive']['rmse']:.2f}** | **{ov['ridge_regression_recursive']['mape']:.2f}%** | **{ov['ridge_regression_recursive']['mase']:.4f}** |
| **XGBoost Regressor** | Recursive Autoregressive | **{ov['xgboost_recursive']['mae']:.2f}** | **{ov['xgboost_recursive']['rmse']:.2f}** | **{ov['xgboost_recursive']['mape']:.2f}%** | **{ov['xgboost_recursive']['mase']:.4f}** |

---

## 3. Horizon-Specific Breakdown (Steps 1 through 7)
Tracking error compounding as the recursive forecast horizon extends:

| Horizon Step ($h$) | Seasonal Naive MAE | Ridge Recursive MAE | XGBoost Recursive MAE | Seasonal Naive MASE | Ridge MASE | XGBoost MASE |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for row in summary["horizon_breakdown"]:
        report_content += (
            f"| Day {row['horizon_step']} | {row['snaive_mae']:.2f} | {row['ridge_mae']:.2f} | {row['xgb_mae']:.2f} "
            f"| {row['snaive_mase']:.4f} | {row['ridge_mase']:.4f} | {row['xgb_mase']:.4f} |\n"
        )

    report_content += f"""
---

## 4. Key Empirical Findings
1. **Longitudinal Robustness Across a Full Year:** Unlike a single 7-day holdout, evaluating 52 origins encompasses autumn surges, winter peaks, and spring lulls across California acute-care facilities.
2. **Error Growth by Horizon:** Autoregressive ML models compound error as the recursive horizon advances from Step 1 to Step 7.
3. **MASE Benchmarking:** MASE scores relative to in-sample seasonal scaling confirm whether machine learning provides substantial advantages over periodic persistence.

---

## 5. Artifacts and Data Provenance
- Metrics JSON: `{json_path}`
- Detailed Predictions CSV: `{preds_path}`
- Horizon Metrics CSV: `{horizons_path}`
- Per-Origin Summary CSV: `{origins_path}`
- Horizon Performance Plot: `{plot_path}`
"""

    with open(report_path, "w") as f:
        f.write(report_content)

    return {
        "metrics_json": json_path,
        "predictions_csv": preds_path,
        "horizons_csv": horizons_path,
        "origins_csv": origins_path,
        "plot_png": plot_path,
        "report_md": report_path
    }


if __name__ == "__main__":
    results = run_rolling_origin_evaluation()
    saved = save_rolling_experiment_artifacts(results)
    print("\nRolling Origin Evaluation Complete!")
    print(f"Artifacts saved in: {ROLLING_OUTPUTS_DIR}")
    for k, v in saved.items():
        print(f"  {k}: {v}")
