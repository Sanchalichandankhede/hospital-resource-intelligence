import os
import pytest
import pandas as pd
import numpy as np

from ml.preprocessing.california_capacity import (
    clean_california_capacity,
    clean_numeric_series,
    DEFAULT_RAW_PATH,
    DEFAULT_PROCESSED_PATH
)
from ml.forecasting.california_capacity_experiment import (
    build_training_features,
    extract_features_for_row,
    run_recursive_forecast,
    evaluate_forecasting_models,
    generate_future_7day_recursive_forecast,
    run_full_california_experiment
)


# =====================================================================
# 1. DATA PREPARATION TESTS
# =====================================================================

def test_data_preparation_filtering_and_conversion():
    """
    Verifies:
    - Only CA records are included.
    - inpatient_beds and inpatient_beds_used are numeric dtypes.
    - Comma-separated strings are cleanly converted without NaNs.
    - Processed CSV exists and contains expected columns.
    """
    df, summary = clean_california_capacity(save=False)

    assert not df.empty, "Cleaned California dataframe should not be empty."
    assert (df["state"] == "CA").all(), "All records must have state == 'CA'."
    assert len(df) == 1524, f"Expected 1,524 CA records, got {len(df)}."

    # Verify numeric conversion
    assert pd.api.types.is_numeric_dtype(df["inpatient_beds"]), "inpatient_beds must be numeric."
    assert pd.api.types.is_numeric_dtype(df["inpatient_beds_used"]), "inpatient_beds_used must be numeric."

    # Check that commas are gone and values are within expected reasonable range
    assert df["inpatient_beds"].min() > 0, "inpatient_beds should be positive."
    assert df["inpatient_beds_used"].min() > 0, "inpatient_beds_used should be positive."
    assert df["inpatient_beds_used"].max() < 100000, "inpatient_beds_used should be within realistic hospital limits."


def test_clean_numeric_series_helper():
    """Tests the string-to-numeric cleaning utility directly."""
    test_series = pd.Series(["63,704", "1,200", "50", 100, 250.5])
    cleaned = clean_numeric_series(test_series)
    expected = pd.Series([63704.0, 1200.0, 50.0, 100.0, 250.5])
    pd.testing.assert_series_equal(cleaned, expected)


def test_processed_csv_file_persistence():
    """Verifies that the processed CSV is saved to data/processed/california_hospital_capacity_daily.csv."""
    assert os.path.exists(DEFAULT_PROCESSED_PATH), f"File {DEFAULT_PROCESSED_PATH} must exist."
    persisted_df = pd.read_csv(DEFAULT_PROCESSED_PATH)
    assert len(persisted_df) == 1524
    assert "date" in persisted_df.columns
    assert "state" in persisted_df.columns
    assert "inpatient_beds_used" in persisted_df.columns
    assert "inpatient_beds" in persisted_df.columns


# =====================================================================
# 2. DATE ORDERING & PARSING TESTS
# =====================================================================

def test_date_ordering_and_chronological_sort():
    """
    Verifies:
    - date is parsed properly into standard format.
    - Dates are strictly monotonically increasing chronologically.
    - Earliest date is 2020-02-04 and latest date is 2024-04-27.
    """
    df, _ = clean_california_capacity(save=False)
    parsed_dates = pd.to_datetime(df["date"])

    # Strict monotonicity check
    assert parsed_dates.is_monotonic_increasing, "Observations must be strictly sorted chronologically."
    assert str(df["date"].iloc[0]) == "2020-02-04"
    assert str(df["date"].iloc[-1]) == "2024-04-27"

    # Verify that in the continuous portion (from 2020-03-01 onwards), date difference is strictly 1 day
    cont_dates = parsed_dates[parsed_dates >= "2020-03-01"]
    diffs = cont_dates.diff().dropna()
    assert (diffs == pd.Timedelta(days=1)).all(), "Dates from 2020-03-01 to 2024-04-27 must be consecutive daily."


# =====================================================================
# 3. MISSING VALUES & INTEGRITY CHECKS (NO SILENT FILL)
# =====================================================================

def test_zero_missing_targets_in_processed():
    """Verifies that no missing targets or capacities exist in the cleaned California data."""
    df, summary = clean_california_capacity(save=False)
    assert summary["missing_targets"] == 0
    assert df["inpatient_beds_used"].isna().sum() == 0
    assert df["inpatient_beds"].isna().sum() == 0


def test_validation_rejects_missing_targets_without_silent_fill(tmp_path):
    """
    Verifies requirement: 'Do not silently fill missing targets.'
    If the target contains missing values, clean_california_capacity must raise ValueError,
    rather than silently filling or interpolating them.
    """
    # Create synthetic raw CSV with missing target
    synthetic_raw = tmp_path / "bad_capacity.csv"
    df_raw = pd.DataFrame({
        "state": ["CA", "CA", "CA"],
        "date": ["2021-01-01", "2021-01-02", "2021-01-03"],
        "inpatient_beds": ["60,000", "60,000", "60,000"],
        "inpatient_beds_used": ["40,000", np.nan, "42,000"]
    })
    df_raw.to_csv(synthetic_raw, index=False)

    with pytest.raises(ValueError, match="missing values in target 'inpatient_beds_used'"):
        clean_california_capacity(raw_path=str(synthetic_raw), save=False)


def test_validation_rejects_duplicate_california_dates(tmp_path):
    """Verifies that duplicate dates for California raise a ValueError."""
    synthetic_raw = tmp_path / "duplicate_dates.csv"
    df_raw = pd.DataFrame({
        "state": ["CA", "CA"],
        "date": ["2021-01-01", "2021-01-01"],  # Duplicate date
        "inpatient_beds": ["60,000", "60,000"],
        "inpatient_beds_used": ["40,000", "41,000"]
    })
    df_raw.to_csv(synthetic_raw, index=False)

    with pytest.raises(ValueError, match="duplicate California date records"):
        clean_california_capacity(raw_path=str(synthetic_raw), save=False)


def test_validation_rejects_invalid_negative_bed_values(tmp_path):
    """Verifies that negative bed or capacity counts raise a ValueError."""
    synthetic_raw = tmp_path / "negative_beds.csv"
    df_raw = pd.DataFrame({
        "state": ["CA"],
        "date": ["2021-01-01"],
        "inpatient_beds": ["60,000"],
        "inpatient_beds_used": ["-500"]  # Negative value
    })
    df_raw.to_csv(synthetic_raw, index=False)

    with pytest.raises(ValueError, match="negative bed counts"):
        clean_california_capacity(raw_path=str(synthetic_raw), save=False)


def test_validation_rejects_inconsistent_capacity_records(tmp_path):
    """Verifies that inpatient_beds_used > inpatient_beds raises a ValueError."""
    synthetic_raw = tmp_path / "inconsistent_capacity.csv"
    df_raw = pd.DataFrame({
        "state": ["CA"],
        "date": ["2021-01-01"],
        "inpatient_beds": ["50,000"],
        "inpatient_beds_used": ["60,000"]  # Used exceeds capacity
    })
    df_raw.to_csv(synthetic_raw, index=False)

    with pytest.raises(ValueError, match="inconsistent capacity records"):
        clean_california_capacity(raw_path=str(synthetic_raw), save=False)


# =====================================================================
# 4. FORECAST OUTPUT & CAPACITY ASSUMPTION TESTS
# =====================================================================

def test_recursive_7day_forecast_structure_and_horizon():
    """
    Verifies genuine recursive 7-day forecast output:
    - Exactly 7 future days predicted.
    - Dates are consecutive daily starting the day after historical data ends.
    - Values are strictly positive.
    - Capacity and occupancy assumptions are populated.
    """
    df = pd.read_csv(DEFAULT_PROCESSED_PATH)
    forecast_df = generate_future_7day_recursive_forecast(df, model_type="ridge")

    assert len(forecast_df) == 7, "Forecast must contain exactly 7 daily predictions."

    expected_dates = [
        "2024-04-28", "2024-04-29", "2024-04-30",
        "2024-05-01", "2024-05-02", "2024-05-03", "2024-05-04"
    ]
    assert list(forecast_df["date"]) == expected_dates, f"Forecast dates mismatch. Expected {expected_dates}."

    assert (forecast_df["forecast_inpatient_beds_used"] > 0).all(), "All forecast values must be positive."
    assert (forecast_df["projected_occupancy_pct"] > 0).all(), "Projected occupancy rate must be positive."
    assert (forecast_df["projected_occupancy_pct"] <= 100.0).all(), "Projected occupancy should be <= 100%."
    assert "capacity_assumption" in forecast_df.columns, "Must document capacity assumptions in output."


def test_model_evaluation_metrics_and_comparison():
    """
    Verifies the evaluation pipeline:
    - Evaluates baseline and ML model on the exact same test dates.
    - Computes MAE and RMSE.
    - Records sample count and test period.
    """
    df = pd.read_csv(DEFAULT_PROCESSED_PATH)
    results = evaluate_forecasting_models(df, test_horizon=7)

    report = results["report"]
    assert report["test_period"]["sample_count"] == 7
    assert report["test_period"]["start_date"] == "2024-04-21"
    assert report["test_period"]["end_date"] == "2024-04-27"

    metrics = report["model_metrics"]
    assert "weekly_seasonal_naive" in metrics
    assert "ridge_regression_recursive" in metrics
    assert "xgboost_recursive" in metrics

    # Verify both MAE and RMSE are computed and positive
    for model_key in ["weekly_seasonal_naive", "ridge_regression_recursive", "xgboost_recursive"]:
        assert metrics[model_key]["mae"] > 0
        assert metrics[model_key]["rmse"] > 0
        assert metrics[model_key]["rmse"] >= metrics[model_key]["mae"], "RMSE must be >= MAE by Cauchy-Schwarz."

    # Verify exact same dates in comparison dataframe
    comp_df = results["comparison_df"]
    assert len(comp_df) == 7
    assert list(comp_df["date"]) == [
        "2024-04-21", "2024-04-22", "2024-04-23", "2024-04-24", "2024-04-25", "2024-04-26", "2024-04-27"
    ]


# =====================================================================
# 5. DATA LEAKAGE PREVENTION TESTS
# =====================================================================

def test_leakage_prevention_train_test_chronological_boundary():
    """
    Verifies that the chronological train/test split has zero overlap
    and that all train dates strictly precede all test dates.
    """
    df = pd.read_csv(DEFAULT_PROCESSED_PATH)
    df["date"] = pd.to_datetime(df["date"])
    ca_cont = df[df["date"] >= "2020-03-01"].sort_values("date").reset_index(drop=True)

    test_horizon = 7
    train_df = ca_cont.iloc[:-test_horizon]
    test_df = ca_cont.iloc[-test_horizon:]

    assert train_df["date"].max() < test_df["date"].min(), "Train period must strictly precede test period."
    assert (test_df["date"].min() - train_df["date"].max()) == pd.Timedelta(days=1), "Boundary must be consecutive."


def test_leakage_prevention_in_feature_engineering():
    """
    Verifies that feature engineering creates features strictly from past data:
    - rolling_mean_7 is shifted by 1 day (does NOT include day t).
    - lag_1, lag_2, lag_7, lag_14 use only past observations.
    - contemporaneous capacity is excluded from feature set.
    """
    synthetic_df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=30, freq="D"),
        "inpatient_beds_used": list(range(100, 130)),
        "inpatient_beds": [200] * 30
    })

    feats_df, feat_cols = build_training_features(synthetic_df)

    # Inpatient beds capacity must NOT be in feature set to prevent capacity leakage
    assert "inpatient_beds" not in feat_cols, "Capacity must be excluded from autoregressive feature inputs."

    # Check that row at index 0 (which corresponds to 15th observation after dropna)
    # has rolling_mean_7 equal to mean of previous 7 days (not including current day)
    # For synthetic series 100..129:
    # row date 2024-01-15 (value 114): rolling_mean_7 must be mean of [107, 108, 109, 110, 111, 112, 113] = 110.0
    row_15 = feats_df[feats_df["date"] == pd.Timestamp("2024-01-15")].iloc[0]
    expected_mean = np.mean(list(range(107, 114)))
    assert np.isclose(row_15["rolling_mean_7"], expected_mean), "rolling_mean must strictly use past observations (shift 1)."
    assert row_15["lag_1"] == 113, "lag_1 must be exactly the previous day value."


def test_recursive_forecast_does_not_access_future_ground_truth():
    """
    Verifies genuine recursive behavior:
    Masking, altering, or withholding future ground truth in the test set
    produces identical recursive predictions.
    """
    df = pd.read_csv(DEFAULT_PROCESSED_PATH)
    eval_original = evaluate_forecasting_models(df, test_horizon=7)
    original_ridge_preds = eval_original["comparison_df"]["ridge_recursive_predicted"].values

    # Now alter the target values of the last 7 days in the dataset to random extreme values (e.g. 999,999)
    df_corrupted = df.copy()
    df_corrupted.iloc[-7:, df_corrupted.columns.get_loc("inpatient_beds_used")] = 999999.0

    # The evaluation function trains on iloc[:-7] and recursively projects over 7 steps
    eval_corrupted = evaluate_forecasting_models(df_corrupted, test_horizon=7)
    corrupted_ridge_preds = eval_corrupted["comparison_df"]["ridge_recursive_predicted"].values

    # Predictions MUST be strictly identical because genuine recursive forecasting
    # never queries the future ground truth values!
    np.testing.assert_allclose(
        original_ridge_preds,
        corrupted_ridge_preds,
        err_msg="Recursive forecast must be identical regardless of future ground truth values."
    )
