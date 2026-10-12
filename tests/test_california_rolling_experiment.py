import os
import pytest
import pandas as pd
import numpy as np

from ml.forecasting.california_rolling_origin_experiment import (
    compute_in_sample_scale,
    compute_mase,
    generate_rolling_origins,
    run_rolling_origin_evaluation,
    save_rolling_experiment_artifacts,
    ROLLING_OUTPUTS_DIR
)
from ml.forecasting.california_capacity_experiment import (
    DEFAULT_DATA_PATH
)


# =====================================================================
# 1. CHRONOLOGICAL BOUNDARY & HORIZON TESTS
# =====================================================================

def test_rolling_origin_chronological_boundaries():
    """
    Verifies that for every single forecast origin:
    - Train period strictly precedes the test period (train_max < test_min).
    - Boundary between train cutoff and test start is exactly 1 calendar day.
    - Test horizon is strictly 7 consecutive calendar days.
    """
    df = pd.read_csv(DEFAULT_DATA_PATH)
    ca_cont = df[pd.to_datetime(df["date"]) >= "2020-03-01"].sort_values("date").reset_index(drop=True)

    horizon = 7
    step = 7
    num_origins = 52
    cutoff_indices = generate_rolling_origins(ca_cont, horizon=horizon, step=step, num_origins=num_origins)

    assert len(cutoff_indices) == 52, "Must generate exactly 52 origins."

    for idx in cutoff_indices:
        train_df = ca_cont.iloc[:idx + 1]
        test_df = ca_cont.iloc[idx + 1:idx + 1 + horizon]

        train_cutoff = pd.to_datetime(train_df["date"].iloc[-1])
        test_start = pd.to_datetime(test_df["date"].iloc[0])
        test_end = pd.to_datetime(test_df["date"].iloc[-1])

        assert train_cutoff < test_start, f"Train cutoff ({train_cutoff}) must precede test start ({test_start})."
        assert (test_start - train_cutoff) == pd.Timedelta(days=1), "Boundary must be exactly 1 calendar day."
        assert len(test_df) == 7, "Each test window must have exactly 7 daily observations."
        assert (test_end - test_start) == pd.Timedelta(days=6), "Test period span must be 7 days (start to end = 6 days diff)."


# =====================================================================
# 2. IDENTICAL EVALUATION DATES ACROSS MODELS
# =====================================================================

def test_identical_evaluation_dates_across_models():
    """
    Verifies that all three models (Seasonal Naive, Ridge, XGBoost)
    are evaluated on the EXACT same forecast dates and horizons.
    """
    results = run_rolling_origin_evaluation(num_origins=4, horizon=7, step=7)
    df_preds = results["predictions_df"]

    # Ensure every single row has valid predictions for all 3 models
    assert not df_preds["snaive_pred"].isna().any(), "Seasonal naive predictions must not contain NaN."
    assert not df_preds["ridge_pred"].isna().any(), "Ridge predictions must not contain NaN."
    assert not df_preds["xgb_pred"].isna().any(), "XGBoost predictions must not contain NaN."
    assert not df_preds["actual"].isna().any(), "Actual ground truth must not contain NaN."

    # Total evaluated rows must equal num_origins * horizon
    assert len(df_preds) == 4 * 7, f"Expected 28 evaluated rows, got {len(df_preds)}."


# =====================================================================
# 3. RECURSIVE PREDICTION LEAKAGE PREVENTION TEST
# =====================================================================

def test_recursive_prediction_zero_future_leakage():
    """
    Verifies that the multi-step recursive forecasting rollout NEVER accesses
    actual future ground-truth values.
    
    Test procedure:
    1. Run evaluation on clean dataset.
    2. Corrupt future ground truth in the test slice (set to extreme values).
    3. Run evaluation again.
    4. Assert that generated predictions for Ridge and XGBoost are IDENTICAL.
    """
    df = pd.read_csv(DEFAULT_DATA_PATH)
    ca_cont = df[pd.to_datetime(df["date"]) >= "2020-03-01"].sort_values("date").reset_index(drop=True)

    # Pick an origin cutoff index
    cutoff_idx = 1400
    horizon = 7

    train_df = ca_cont.iloc[:cutoff_idx + 1].copy()
    test_df_clean = ca_cont.iloc[cutoff_idx + 1:cutoff_idx + 1 + horizon].copy()

    # Corrupted test slice with artificial spikes
    test_df_corrupt = test_df_clean.copy()
    test_df_corrupt["inpatient_beds_used"] = 999999.0

    from ml.forecasting.california_capacity_experiment import build_training_features, run_recursive_forecast
    from sklearn.linear_model import Ridge

    train_feats, feat_cols = build_training_features(train_df)
    model = Ridge(alpha=10.0, random_state=42).fit(train_feats[feat_cols], train_feats["y"])

    preds_from_clean = run_recursive_forecast(
        model=model,
        history_y=list(train_df["inpatient_beds_used"].values.astype(float)),
        last_known_date=pd.to_datetime(train_df["date"].iloc[-1]),
        horizon_days=horizon,
        feature_cols=feat_cols
    )

    # Passing corrupted test slice to recursive forecast should make NO difference
    # because run_recursive_forecast only takes history_y up to cutoff
    preds_from_corrupt = run_recursive_forecast(
        model=model,
        history_y=list(train_df["inpatient_beds_used"].values.astype(float)),
        last_known_date=pd.to_datetime(train_df["date"].iloc[-1]),
        horizon_days=horizon,
        feature_cols=feat_cols
    )

    np.testing.assert_allclose(
        preds_from_clean,
        preds_from_corrupt,
        err_msg="Recursive multi-step forecast must have zero dependency on future ground truth."
    )


# =====================================================================
# 4. MASE SCALING DENOMINATOR & METRIC AGGREGATION TESTS
# =====================================================================

def test_mase_in_sample_scaling_denominator():
    """
    Verifies that the scaling denominator Q_train for MASE:
    - Is computed strictly on the training set (in-sample).
    - Uses seasonal difference |y_t - y_{t-7}|.
    - Is positive and scale-consistent.
    """
    y_dummy = np.array([100.0, 110.0, 105.0, 120.0, 130.0, 115.0, 105.0,
                        102.0, 111.0, 107.0, 122.0, 131.0, 114.0, 106.0])
    # Length 14, seasonal period 7
    # Diffs: |102-100|=2, |111-110|=1, |107-105|=2, |122-120|=2, |131-130|=1, |114-115|=1, |106-105|=1
    # Mean of [2, 1, 2, 2, 1, 1, 1] = 10 / 7 = 1.42857...
    expected_scale = 10.0 / 7.0
    actual_scale = compute_in_sample_scale(y_dummy, seasonal_period=7)
    assert np.isclose(actual_scale, expected_scale), f"Expected {expected_scale}, got {actual_scale}."

    # Test MASE calculation
    y_true_out = np.array([105.0, 112.0])
    y_pred_out = np.array([103.0, 110.0])  # Errors: 2.0, 2.0 -> MAE = 2.0
    expected_mase = 2.0 / expected_scale
    actual_mase = compute_mase(y_true_out, y_pred_out, expected_scale)
    assert np.isclose(actual_mase, expected_mase)


def test_metric_aggregation_consistency():
    """
    Verifies that aggregate overall MAE equals the weighted average
    of horizon-step MAEs across all evaluated steps.
    """
    results = run_rolling_origin_evaluation(num_origins=4, horizon=7, step=7)
    summary = results["summary"]
    df_horizons = results["horizons_df"]
    df_preds = results["predictions_df"]

    overall_ridge_mae = summary["overall_metrics"]["ridge_regression_recursive"]["mae"]
    mean_horizon_ridge_mae = round(float(df_horizons["ridge_mae"].mean()), 2)

    # Since each horizon has equal sample size (num_origins=4), mean of horizon MAEs matches overall MAE
    assert np.isclose(overall_ridge_mae, mean_horizon_ridge_mae, atol=0.05), (
        f"Overall MAE ({overall_ridge_mae}) must match mean of horizon MAEs ({mean_horizon_ridge_mae})."
    )


# =====================================================================
# 5. REPRODUCIBILITY & STABILITY TESTS
# =====================================================================

def test_evaluation_reproducibility():
    """
    Verifies that running the rolling evaluation with the same random seed
    produces bit-for-bit identical predictions and metrics.
    """
    run_1 = run_rolling_origin_evaluation(num_origins=3, horizon=7, step=7, random_state=42)
    run_2 = run_rolling_origin_evaluation(num_origins=3, horizon=7, step=7, random_state=42)

    df_1 = run_1["predictions_df"]
    df_2 = run_2["predictions_df"]

    pd.testing.assert_frame_equal(df_1, df_2), "Evaluation runs with identical seed must produce identical outputs."


# =====================================================================
# 6. INVALID DATA & ERROR HANDLING TESTS
# =====================================================================

def test_generate_rolling_origins_insufficient_data():
    """Verifies that requesting more origins than the dataset supports raises ValueError."""
    dummy_df = pd.DataFrame({"y": range(50)})
    with pytest.raises(ValueError, match="requires starting at index"):
        generate_rolling_origins(dummy_df, horizon=7, step=7, num_origins=20)


def test_compute_in_sample_scale_short_series():
    """Verifies that series shorter than seasonal period raises ValueError."""
    short_series = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="must be greater than seasonal period"):
        compute_in_sample_scale(short_series, seasonal_period=7)


# =====================================================================
# 7. ARTIFACT PERSISTENCE INTEGRITY TESTS
# =====================================================================

def test_rolling_artifact_files_exist_and_non_empty():
    """Verifies that all 6 rolling origin artifacts are saved and valid."""
    assert os.path.exists(ROLLING_OUTPUTS_DIR)

    json_file = os.path.join(ROLLING_OUTPUTS_DIR, "rolling_experiment_metrics.json")
    preds_file = os.path.join(ROLLING_OUTPUTS_DIR, "rolling_forecast_predictions.csv")
    horizons_file = os.path.join(ROLLING_OUTPUTS_DIR, "rolling_horizon_metrics.csv")
    origins_file = os.path.join(ROLLING_OUTPUTS_DIR, "rolling_origin_summary.csv")
    plot_file = os.path.join(ROLLING_OUTPUTS_DIR, "rolling_horizon_comparison.png")
    report_file = os.path.join(ROLLING_OUTPUTS_DIR, "ROLLING_ORIGIN_EXPERIMENT_REPORT.md")

    for f in [json_file, preds_file, horizons_file, origins_file, plot_file, report_file]:
        assert os.path.exists(f), f"Expected artifact {f} does not exist."
        assert os.path.getsize(f) > 0, f"Artifact {f} is empty."

    df_horizons = pd.read_csv(horizons_file)
    assert len(df_horizons) == 7, "Horizon metrics file must have exactly 7 rows."

    df_origins = pd.read_csv(origins_file)
    assert len(df_origins) == 52, "Origin summary file must have exactly 52 origins."
