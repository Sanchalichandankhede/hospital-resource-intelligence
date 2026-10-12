import os
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DEFAULT_RAW_PATH = os.path.join(PROJECT_ROOT, "data", "raw", "external", "hospital_capacity.csv")
DEFAULT_PROCESSED_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "california_hospital_capacity_daily.csv")


def clean_numeric_series(series: pd.Series) -> pd.Series:
    """
    Converts comma-separated string numbers (e.g. '63,704') to numeric float values.
    """
    if series.dtype == object:
        cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
        # Handle empty strings or non-numeric representations as NaN
        return pd.to_numeric(cleaned, errors="coerce")
    return pd.to_numeric(series, errors="coerce")


def clean_california_capacity(
    raw_path: str = DEFAULT_RAW_PATH,
    output_path: Optional[str] = DEFAULT_PROCESSED_PATH,
    save: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Preprocesses California hospital capacity data:
    1. Loads dataset and filters state == 'CA'.
    2. Parses dates and sorts chronologically.
    3. Converts inpatient_beds_used and inpatient_beds to numeric values.
    4. Validates:
       - No missing values in target or key columns (does NOT silently fill missing targets).
       - No duplicate California dates.
       - No invalid negative bed values.
       - No inconsistent capacity records (inpatient_beds_used > inpatient_beds).
    5. Saves cleaned dataset to data/processed/california_hospital_capacity_daily.csv.

    Returns:
        Tuple of (cleaned_dataframe, validation_summary_dict)
    """
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw dataset not found at: {raw_path}")

    # 1. Load CSV with low_memory=False to avoid DtypeWarning on large external data
    df_raw = pd.read_csv(raw_path, low_memory=False)

    # 2. Filter state == 'CA'
    if "state" not in df_raw.columns:
        raise ValueError("Column 'state' missing from raw hospital capacity dataset.")
    ca_df = df_raw[df_raw["state"] == "CA"].copy()

    if ca_df.empty:
        raise ValueError("No records found for state == 'CA' in raw dataset.")

    # 3. Parse date and sort chronologically
    if "date" not in ca_df.columns:
        raise ValueError("Column 'date' missing from California dataset.")
    ca_df["date"] = pd.to_datetime(ca_df["date"])
    ca_df = ca_df.sort_values("date").reset_index(drop=True)

    # Format date as standard ISO YYYY-MM-DD
    ca_df["date_str"] = ca_df["date"].dt.strftime("%Y-%m-%d")

    # 4. Convert inpatient_beds and inpatient_beds_used from comma-separated strings to numeric
    for col in ["inpatient_beds", "inpatient_beds_used"]:
        if col not in ca_df.columns:
            raise ValueError(f"Required capacity column '{col}' missing from California dataset.")
        ca_df[col] = clean_numeric_series(ca_df[col])

    # Convert other common bed/occupancy columns if present
    optional_bed_cols = [
        "total_staffed_adult_icu_beds",
        "staffed_adult_icu_bed_occupancy",
        "inpatient_beds_used_covid"
    ]
    for col in optional_bed_cols:
        if col in ca_df.columns:
            ca_df[col] = clean_numeric_series(ca_df[col])

    # 5. Data Validation & Integrity Checks
    # 5a. Missing targets: DO NOT silently fill missing targets
    missing_targets = int(ca_df["inpatient_beds_used"].isna().sum())
    if missing_targets > 0:
        raise ValueError(
            f"Validation Failed: Found {missing_targets} missing values in target 'inpatient_beds_used'. "
            "Missing targets must not be silently imputed or filled."
        )

    missing_beds = int(ca_df["inpatient_beds"].isna().sum())
    if missing_beds > 0:
        raise ValueError(
            f"Validation Failed: Found {missing_beds} missing values in capacity 'inpatient_beds'. "
            "Capacity values must not be silently imputed."
        )

    # 5b. Duplicate California dates
    dup_mask = ca_df["date"].duplicated(keep=False)
    duplicate_date_count = int(dup_mask.sum())
    if duplicate_date_count > 0:
        duplicate_dates = ca_df.loc[dup_mask, "date_str"].unique().tolist()
        raise ValueError(
            f"Validation Failed: Found {duplicate_date_count} duplicate California date records for dates: {duplicate_dates}."
        )

    # 5c. Invalid values (negative beds or negative bed usage)
    negative_beds = int((ca_df["inpatient_beds"] < 0).sum())
    negative_used = int((ca_df["inpatient_beds_used"] < 0).sum())
    if negative_beds > 0 or negative_used > 0:
        raise ValueError(
            f"Validation Failed: Found negative bed counts (negative capacity: {negative_beds}, negative used: {negative_used})."
        )

    # 5d. Inconsistent capacity records (inpatient_beds_used > inpatient_beds)
    inconsistent_mask = ca_df["inpatient_beds_used"] > ca_df["inpatient_beds"]
    inconsistent_capacity_count = int(inconsistent_mask.sum())
    if inconsistent_capacity_count > 0:
        inconsistent_dates = ca_df.loc[inconsistent_mask, "date_str"].tolist()
        raise ValueError(
            f"Validation Failed: Found {inconsistent_capacity_count} inconsistent capacity records where inpatient_beds_used > inpatient_beds on dates: {inconsistent_dates}."
        )

    # Use formatted date string for clean storage
    ca_df["date"] = ca_df["date_str"]
    ca_df = ca_df.drop(columns=["date_str"])

    # 6. Save cleaned dataset
    if save and output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ca_df.to_csv(output_path, index=False)

    summary = {
        "raw_file": raw_path,
        "processed_file": output_path if save else None,
        "total_records": len(ca_df),
        "state": "CA",
        "date_min": str(ca_df["date"].min()),
        "date_max": str(ca_df["date"].max()),
        "missing_targets": missing_targets,
        "duplicate_dates": duplicate_date_count,
        "invalid_negative_values": negative_beds + negative_used,
        "inconsistent_capacity_records": inconsistent_capacity_count,
        "inpatient_beds_used_mean": float(ca_df["inpatient_beds_used"].mean()),
        "inpatient_beds_used_min": float(ca_df["inpatient_beds_used"].min()),
        "inpatient_beds_used_max": float(ca_df["inpatient_beds_used"].max()),
        "inpatient_beds_capacity_mean": float(ca_df["inpatient_beds"].mean()),
    }

    return ca_df, summary


if __name__ == "__main__":
    print("Running California hospital capacity cleaning pipeline...")
    df, report = clean_california_capacity()
    print("Cleaning completed successfully:")
    for k, v in report.items():
        print(f"  {k}: {v}")
