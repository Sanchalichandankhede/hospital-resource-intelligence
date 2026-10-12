# Database Import and Setup Plan

This folder contains the PostgreSQL database schema definitions and instructions on how to load existing CSV and JSON outputs generated from ML preprocessing, evaluation, and shortage modules into PostgreSQL.

---

## 1. Schema Installation

To install the database schema, run the following SQL command against your PostgreSQL instance:

```bash
psql -h localhost -U your_username -d your_database -f database/schema.sql
```

This creates the normalized tables, indexes, constraints, and validation structures.

---

## 2. CSV & JSON Data Import Strategy

Data import will be implemented in a dedicated migration/seed script using Python (`psycopg2` or `SQLAlchemy` + `pandas`). Below is the mapping plan from existing files to SQL entities.

### A. Preprocessed Historical Demand
* **Source Files:**
  - `data/processed/icu_daily_processed.csv` (columns: `date`, `occupied_beds`)
  - `data/processed/ed_daily_processed.csv` (columns: `date`, `arrivals`)
* **SQL Target:** `historical_demand` table.
* **Mapping Logic:**
  - ICU: `date` $\to$ `date`, `occupied_beds` $\to$ `actual_demand`, `'ICU Beds'` $\to$ `resource`, `'occupancy'` $\to$ `target_type`.
  - ED: `date` $\to$ `date`, `arrivals` $\to$ `actual_demand`, `'ED Arrivals'` $\to$ `resource`, `'arrivals'` $\to$ `target_type`.
* **Insert/Upsert Mode:** `INSERT ... ON CONFLICT (date, resource) DO UPDATE`.

### B. Forecast Data
* **Source Files:**
  - `data/interim/prophet_icu_forecast.csv`
  - `data/interim/prophet_ed_forecast.csv`
  - `data/interim/xgboost_icu_forecast.csv`
  - `data/interim/xgboost_ed_forecast.csv`
  - `data/interim/lstm_icu_forecast.csv`
  - `data/interim/lstm_ed_forecast.csv`
* **SQL Target:** `forecasts` table.
* **Mapping Logic:**
  - `date` $\to$ `forecast_date`
  - `predicted` $\to$ `predicted_demand`
  - `actual` $\to$ `actual_demand`
  - Model name extracted from filename (e.g., `'Prophet'`, `'XGBoost'`, or `'LSTM'`).
  - Resource name based on target type (e.g. `'ICU Beds'` or `'ED Arrivals'`).
  - `forecast_horizon` set to `'7 days'`.

### C. Model Performance Summary
* **Source File:** `ml/evaluation/model_comparison.csv`
* **SQL Target:** `model_performance` table.
* **Mapping Logic:**
  - `target` $\to$ `target` (e.g., `'icu_occupancy'`, `'ed_arrivals'`)
  - `model` $\to$ `model`
  - `mae` $\to$ `mae`
  - `rmse` $\to$ `rmse`
  - `mape` $\to$ `mape`
  - `mae_rank` $\to$ `rank`
  - `evaluation_period` mapped to standard descriptive text (e.g., `'Holdout Evaluation Horizon (7 days)'`).

### D. Resource Shortage Alerts
* **Source File:** `outputs/alerts/resource_alerts.csv` (columns: `date`, `resource`, `predicted_demand`, `available_capacity`, `capacity_gap`, `risk_level`, `reason`)
* **SQL Target:** `alerts` table.
* **Mapping Logic:**
  - `date` $\to$ `alert_date`
  - `resource` $\to$ `resource`
  - `predicted_demand` $\to$ `predicted_demand`
  - `actual_capacity` $\to$ Set to `NULL` (since no physical bed/ward metrics exist in raw extracts).
  - `available_capacity` $\to$ `simulated_capacity`
  - `is_capacity_simulated` $\to$ `TRUE` (indicates administrative simulation context).
  - `capacity_gap` $\to$ `capacity_gap`
  - `risk_level` $\to$ `risk_level`
  - `reason` $\to$ `reason`

### E. Operational Recommendations
* **Source File:** `outputs/recommendations/recommendations.csv` (columns: `date`, `resource`, `risk_level`, `recommendation`, `trigger`, `model`)
* **SQL Target:** `recommendations` table.
* **Mapping Logic:**
  - Fetch corresponding `alerts.id` using `(date, resource)` to populate `alert_id` foreign key.
  - `date` $\to$ `date`
  - `resource` $\to$ `resource`
  - `risk_level` $\to$ `risk_level`
  - `recommendation` $\to$ `recommendation`
  - `trigger` $\to$ `trigger`
  - `model` $\to$ `model`

### F. Explainability Vectors (XAI local)
* **Source Files:**
  - `outputs/explainability/shap/icu_local.csv`
  - `outputs/explainability/shap/ed_local.csv`
  - `outputs/explainability/lime/icu_local.csv`
  - `outputs/explainability/lime/ed_local.csv`
* **SQL Target:** `explanations` table.
* **Mapping Logic:**
  - File path defines `resource` (`'ICU Beds'` / `'ED Arrivals'`) and `explanation_method` (`'SHAP'` / `'LIME'`).
  - Date is mapped matching the target forecast dates (Stage 9 evaluation date).
  - `feature` $\to$ `feature`
  - `value` $\to$ `feature_value`
  - `contribution` $\to$ `contribution`
  - `direction` $\to$ `direction`

### G. Model Metadata
* **Source Files:**
  - `ml/forecasting/xgboost/feature_importance.json` (keys: `icu`, `ed`)
  - `ml/forecasting/lstm/loss_history.json`
  - `outputs/explainability/shap/icu_global.csv` and `shap/ed_global.csv`
* **SQL Target:** `model_metadata` table.
* **Mapping Logic:**
  - XGBoost feature importance: key feature name $\to$ `feature`, importance weight $\to$ `value`, `'global_importance'` $\to$ `metadata_type`.
  - LSTM loss history: load training history array $\to$ `json_data`, `'loss_history'` $\to$ `metadata_type`.
  - Global SHAP: feature name $\to$ `feature`, mean SHAP $\to$ `value`, `'global_shap_importance'` $\to$ `metadata_type`.

---

## 3. Reference Implementation (Mock Python Loader script)

When migrations are initiated in Stage 10B, a loader script will execute operations resembling the following routine:

```python
import pandas as pd
import psycopg2

def load_historical_demand(conn, csv_path, resource_name, target_type):
    df = pd.read_csv(csv_path)
    cur = conn.cursor()
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO historical_demand (date, resource, actual_demand, target_type)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (date, resource) 
            DO UPDATE SET actual_demand = EXCLUDED.actual_demand;
        """, (row['date'], resource_name, row['arrivals'] if 'arrivals' in row else row['occupied_beds'], target_type))
    conn.commit()
    cur.close()
```

> [!IMPORTANT]
> **Safety Guard:** Do not run active database connection tests or migrations yet. Stage 10A is strictly restricted to design blueprints, SQL structures, and documentation files.
