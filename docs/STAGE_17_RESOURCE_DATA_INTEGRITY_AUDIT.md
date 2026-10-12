# Stage 17 — Final Resource and Data Integrity Audit
## Hospital Resource Intelligence (HRI)

**Audit Execution Date:** October 12, 2026  
**Auditor:** Automated Codebase & Research Pipeline Auditor  
**Audit Scope:** Data provenance, seven-resource pipeline validity, California experiment verification, API/UI labeling accuracy, and defect categorization.  
**Mode:** Strict Read-Only Audit (Zero modifications to models, datasets, or production logic).

---

## 1. Executive Summary and Overall Readiness Verdict

### Overall Readiness Verdict: **CONDITIONAL PASS (DEMONSTRATION READY; DUAL-TRACK ARCHITECTURE DISCLOSED)**

The Hospital Resource Intelligence (HRI) platform is structurally stable and fully operational from an engineering perspective (75/75 automated unit tests passing, 10 standalone validation scripts passing, zero backend/frontend startup errors). However, a comprehensive audit reveals that the project consists of **two distinct, decoupled tracks**:

1. **The Academic Research Track (California Statewide Hospital Capacity):**
   * **Scope:** 1,544 continuous daily observations (Feb 2020 – Apr 2024) of statewide aggregate inpatient bed utilization across ~400 California acute-care facilities.
   * **Validity:** Highly rigorous, leakage-free, chronological evaluation across both a 7-day single holdout and a 52-week rolling-origin experiment (364 non-overlapping evaluated days). All metrics (MAE, RMSE, MAPE, MASE) are independently verified and reproducible.
   * **Limitation:** Macro-level statewide aggregation masking facility-level variation; strictly offline Python research scripts (`ml/forecasting/california_*`) not integrated into the live interactive web dashboard.

2. **The Operational Web Application Track (FastAPI + React Dashboard):**
   * **Scope:** An interactive multi-resource decision support tool monitoring 7 resource categories.
   * **Validity:** Only **two** resources (ICU Beds and ED Arrivals) possess underlying historical data and machine learning forecasting models (XGBoost, Prophet, LSTM), derived from de-identified MIMIC-IV EHR records. The remaining **five** resources (General Beds, Oxygen, Blood, Staff, Ambulances) rely on heuristic conversion formulas derived from ICU and ED outputs.
   * **Limitation:** Inconsistencies exist between formulas used in the backend multi-resource API (`/api/forecast/multi`) and those rendered in dedicated resource dashboard tabs (`BedsDashboard.jsx`, `OxygenDashboard.jsx`, `BloodDashboard.jsx`, `StaffDashboard.jsx`, `AmbulanceDashboard.jsx`). General Beds in `BedsDashboard.jsx` relies on hardcoded static mockup values.

### Platform Readiness Summary
* **Suitable for Research Claims:** California statewide inpatient bed forecasting (single holdout and 52-week rolling origin).
* **Suitable for Interactive Demonstration:** Live dashboard, authentication/RBAC, CSV ingestion, manual data entry, shortage alert engine, and XAI local explanations.
* **Not Suitable for Real Clinical Deployment:** All dashboard forecasts, because they either reflect MIMIC-IV 22nd-century sparse unit data or formula-derived heuristic projections.

---

## 2. Seven-Resource Category Audit Table

| # | Resource Category | Original Source Dataset & Path | Nature of Source Data | Historical Observations Available? | Feature Engineering & Models Used | Horizon & Units | Evaluated Against Future Actuals? | Evaluation Metrics & Source | Suitability Level |
|---|---|---|---|:---:|---|---|:---:|---|---|
| **1** | **ICU Beds** | `data/raw/icu_daily_demand.csv` $\rightarrow$ `data/processed/icu_daily_processed.csv` | Transformed real EHR data (MIMIC-IV, patient dates shifted to 22nd c. 2110–2201, single small unit) | Yes (180 daily records: 2137-04-21 to 2137-10-17; mean: 0.205 beds) | Lags (1, 2, 3, 7, 14), 7-day rolling stats, calendar signals. Models: **XGBoost, Prophet, LSTM** | 7 days (`2137-10-11` to `2137-10-17`). Unit: **Beds** (float $\rightarrow$ $\lceil \text{ceil} \rceil$) | **Yes** (Holdout test set) | XGBoost MAE: **0.5940**, RMSE: **0.6192** (`ml/evaluation/model_comparison.csv`) | **Demonstration / Prototype Only** |
| **2** | **Emergency Department (ED) Beds / Arrivals** | `data/raw/ed_daily_demand.csv` $\rightarrow$ `data/processed/ed_daily_processed.csv` | Transformed real EHR data (MIMIC-IV ED, patient dates shifted to 2112–2201) | Yes (180 daily records: 2147-07-30 to 2148-01-25; mean: 0.072 arrivals) | Lags (1, 2, 3, 7, 14), 7-day rolling stats, calendar signals. Models: **XGBoost, Prophet, LSTM** | 7 days (`2148-01-19` to `2148-01-25`). Unit: **Arrivals / Beds** ($0.25 \times \text{ED}$) | **Yes** (Holdout test set) | XGBoost MAE: **0.2891**, RMSE: **0.5293** (`ml/evaluation/model_comparison.csv`) | **Demonstration / Prototype Only** |
| **3** | **General Beds** | Formally cited as `data/raw/Beds-publication-Timeseries-March-2020-July-2026.xlsx` (NHS England) | Formula-derived heuristic in API; Hardcoded mockup array in dedicated UI tab | **No** (NHS monthly file is not loaded to DB; 0 historical rows in DB) | **No ML Model**. API formula: $18.0 + 2.0 \times \text{ICU}$; Dashboard: Static array `[78, 80, 83, 88, 84, 80, 79]` | 7 days. Unit: **Beds** (Capacity: 25 in API; 150 in UI) | **No** | None (`mae: null`, `rmse: null`) | **Demonstration Only** |
| **4** | **Oxygen** | None (Formula-derived from ICU/ED predictions) | Formula-derived / simulated heuristic | **No** (0 historical rows in DB) | **No ML Model**. API formula: $15.0 \times \text{ICU} + 1.25 \times \text{ED}$; Dashboard formula: $1.5 \times \text{ICU}$ | 7 days. Unit: **Liters** (API) vs **Cylinders** (UI) vs **units** (Alerts) | **No** | None (`mae: null`, `rmse: null`) | **Demonstration Only** |
| **5** | **Blood** | None (Formula-derived from ED/ICU predictions) | Formula-derived / simulated heuristic | **No** (0 historical rows in DB) | **No ML Model**. API formula: $0.20 \times \text{ED}$; Dashboard formula: $0.80 \times \text{ICU}$ | 7 days. Unit: **Units (pints)** (Capacity: 10 in API; 200 in UI) | **No** | None (`mae: null`, `rmse: null`) | **Demonstration Only** |
| **6** | **Staff Requirements** | None (Formula-derived from ICU/ED predictions) | Formula-derived / simulated heuristic | **No** (0 historical rows in DB) | **No ML Model**. API formula: $1.5 \times \text{ICU} + 0.125 \times \text{ED}$; Dashboard formula: $1.2 \times \text{ICU} + 0.4 \times \text{ED}$ | 7 days. Unit: **FTE** (API) vs **Staff Count** (UI) | **No** | None (`mae: null`, `rmse: null`) | **Demonstration Only** |
| **7** | **Ambulance Requirements** | None (Formula-derived from ED arrivals) | Formula-derived / simulated heuristic | **No** (0 historical rows in DB) | **No ML Model**. API formula: $0.15 \times \text{ED}$; Dashboard formula: $\lceil \text{ED} / 6 \rceil$ | 7 days. Unit: **Cars** (API) vs **Ambulances** (UI) | **No** | None (`mae: null`, `rmse: null`) | **Demonstration Only** |

---

## 3. Dataset Provenance and Date-Integrity Findings

### Detailed Dataset File Verification
1. `data/raw/icu_daily_demand.csv` (Exists, 627 rows, 8.4 KB):
   * Columns: `date`, `occupied_beds`.
   * Date range: `2110-04-11` to `2201-12-13`.
   * Values: `occupied_beds` min=1.0, max=2.0, mean=1.0096.
   * **Finding:** Extracted from MIMIC-IV. Dates are subject to HIPAA de-identification random date shifting.
2. `data/raw/ed_daily_demand.csv` (Exists, 221 rows, 2.9 KB):
   * Columns: `date`, `arrivals`.
   * Date range: `2112-09-17` to `2201-10-30`.
   * Values: `arrivals` min=1.0, max=2.0, mean=1.0045.
   * **Finding:** Extracted from MIMIC-IV ED module with random date shifting.
3. `data/raw/Beds-publication-Timeseries-March-2020-July-2026.xlsx` (Exists, 76 monthly rows):
   * Cleaned by `ml/preprocessing/cleaning.py` into `data/processed/beds_monthly_processed.csv`.
   * **Finding:** Represents UK NHS England national monthly acute bed statistics. **Never ingested into the backend application database.**
4. `data/raw/external/hospital_capacity.csv` (Exists, 58.2 MB, 81,713 rows, 135 features):
   * Official HHS COVID-19 Reported Patient Impact and Hospital Capacity by State Timeseries.
   * Filtered for `state == 'CA'` by `ml/preprocessing/california_capacity.py`.
   * **Finding:** Valid real public data source.
5. `data/raw/external/hri_complete_demo_daily.csv` (Exists, 731 rows, dates 2024-01-01 to 2025-12-31):
   * Contains multi-resource simulated data (`is_real_hospital_data: False`).
   * **Finding:** **Orphaned asset.** Not referenced by any script, backend loader, or test in the codebase.
6. `data/processed/california_hospital_capacity_daily.csv` (Exists, 1,544 rows, dates 2020-02-04 to 2024-04-27):
   * Filtered California daily aggregate inpatient capacity and occupied beds (`inpatient_beds`, `inpatient_beds_used`).
   * **Finding:** Core dataset for the California academic research evaluation track.

### Date-Integrity and Cross-Century Pairing Anomaly
* **Preprocessing Window Selection:** In `ml/preprocessing/cleaning.py` (`find_densest_window`), a 180-day continuous window with maximum activity was isolated for ICU (`2137-04-21` to `2137-10-17`) and for ED (`2147-07-30` to `2148-01-25`).
* **Cross-Century Coupling Anomaly:**
  In `backend/routers/multi_resource.py` (lines 186–189):
  ```python
  for i in range(dates_length):
      f_date = icu_forecasts[i].forecast_date  # October 2137!
      icu_val = float(icu_forecasts[i].predicted_demand)  # Year 2137
      ed_val = float(ed_forecasts[i].predicted_demand)    # Year 2148!
  ```
  The endpoint pairs the $i$-th ICU prediction (from year 2137) with the $i$-th ED prediction (from year 2148) by simple array index, and labels the combined multi-resource projection with the 2137 date.
* **Research Implications:**
  * MIMIC-IV random date shifts destroy true multi-year seasonality and calendar alignment.
  * Occupied bed values (0 to 2 beds) represent a single ward or micro-cohort, not a macro hospital census.
  * Cross-pairing predictions from different centuries proves that the multi-resource dashboard is a software demonstration prototype, not an empirical multi-resource clinical validation.

---

## 4. California Forecasting Experiment Audit

### Single-Holdout vs. 52-Week Rolling-Origin Comparison

| Metric / Attribute | Single-Holdout Experiment (`outputs/california_experiment_metrics.json`) | 52-Week Rolling-Origin Experiment (`outputs/rolling_evaluation/rolling_experiment_metrics.json`) | Verification Status |
|---|---|---|:---:|
| **Evaluation Scope** | Single 7-day horizon: April 21–27, 2024 (7 paired test points) | 52 weekly origins: April 30, 2023 – April 27, 2024 (364 paired test points) | **VERIFIED** |
| **Window Geometry** | 1 fixed cutoff ($T = \text{2024-04-20}$) | `step = 7`, `horizon = 7`, forming 52 contiguous, non-overlapping weekly windows | **VERIFIED** |
| **Weekly Seasonal Naive** | MAE: **1154.29**, RMSE: **1375.69**, MAPE: **2.47%** | MAE: **711.47**, RMSE: **1053.72**, MAPE: **1.48%**, MASE: **0.5646** | **VERIFIED** |
| **Ridge Regression** | MAE: **1000.00**, RMSE: **1441.40**, MAPE: **2.15%** | MAE: **727.68**, RMSE: **979.58**, MAPE: **1.51%**, MASE: **0.5757** | **VERIFIED** |
| **XGBoost Regressor** | MAE: **1209.06**, RMSE: **1531.00**, MAPE: **2.59%** | MAE: **639.26**, RMSE: **939.64**, MAPE: **1.33%**, MASE: **0.5072** | **VERIFIED** |
| **Ranked Winner** | **Ridge Regression** wins MAE (1000.00 vs 1154.29); Seasonal Naive wins RMSE | **XGBoost Regressor** wins overall on MAE, RMSE, MAPE, and MASE | **VERIFIED** |
| **Origin 52 Reproducibility**| N/A | Origin 52 exactly reproduces the Single-Holdout predictions (max error: `0.000000`) | **VERIFIED** |

### Methodological Rigor & Leakage Prevention Checks
1. **Chronological Integrity:** Training sets strictly terminate at cutoff $T_k$. No future observations are included in training.
2. **Feature Leakage Prevention:** Lags are strictly positive ($t-1, t-2, \dots$). Rolling means and standard deviations are shifted by 1 day ($t-1$) so they do not incorporate day $t$.
3. **Capacity Leakage Exclusion:** Total inpatient capacity ($C_t$) is omitted from autoregressive features. Cutoff capacity ($C_{T_k}$) is preserved only as an operational context baseline.
4. **Recursive Execution:** Multi-step rollouts for Ridge and XGBoost feed step $\tau$ predictions into step $\tau+1$ feature vectors without accessing true targets.
5. **MASE In-Sample Scaling:** Denominator $Q_{train}$ is calculated strictly on training data up to $T_k$ using lag-7 seasonal differences:
   $$Q_{train} = \frac{1}{n-7}\sum_{t=8}^{n} |y_t - y_{t-7}|$$
6. **Disclosed Limitations:**
   * **Statewide Aggregation:** Represents aggregate utilization across ~400 acute-care facilities, masking regional supply-demand imbalances.
   * **Static Horizon Capacity:** Assumes total capacity remains fixed at $C_{T_k}$ during the 7-day forecast window.

---

## 5. API and Dashboard Labeling Audit

### Compliance Checklist by Component

#### A. Multi-Resource Forecasting Dashboard (`MultiResourceForecasting.jsx`)
* **Resource & Unit Identification:** Displays resource name and unit ("Beds", "Liters", "Units", "FTE", "Cars").
* **Simulated vs. Real Badging:** Clearly displays `SIMULATED / PROTOTYPE` badges alongside amber notice boxes for secondary resources.
* **Disclaimer Notice:** Explicitly states: *"The historical data for this resource is mathematically simulated based on standard hospital load indices. Never use these values for diagnostic decision paths."*
* **Metrics Presentation:** Correctly mutes metrics for simulated targets (`MAE: N/A (Simulated projection)`).
* **Defect Identified:** ICU Demand is badged as `REAL / SOURCE-DERIVED` without disclosing that the underlying observations are from the 22nd century (MIMIC-IV de-identified data).

#### B. Shortage Alerts Table (`AlertTable.jsx`)
* **Capacity Provenance:** Labels capacity as `"Configured Parameter"` for simulated assets and `"Historical Actual"` for real telemetry.
* **Risk Levels:** Displays `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` badges.
* **Defect Identified (Unit Generalization):** Hardcodes `"units"` suffix for all rows:
  ```jsx
  <td><strong>{reqVal}</strong> units</td>
  <td>{capInt} units</td>
  ```
  This causes Oxygen to be displayed as "units" rather than "Liters/Cylinders", and Staff as "units" rather than "FTE/Personnel".
* **Defect Identified (Unconditional Math.ceil):** Applies `Math.ceil()` unconditionally, rounding continuous metrics (e.g. Oxygen liters) into integers in the UI.

#### C. Dedicated Resource Dashboards vs. Multi-Resource View Discrepancies
* **General Beds Discrepancy:**
  * In `MultiResourceForecasting.jsx`: Derived dynamically via $18.0 + 2.0 \times \text{ICU}$; capacity is 25 beds.
  * In `BedsDashboard.jsx`: Hardcoded static dummy array `[78, 80, 83, 88, 84, 80, 79]`; capacity is 150 beds.
* **Oxygen Discrepancy:**
  * In `multi_resource.py`: Capacity = 100.0 Liters; formula = $15.0 \times \text{ICU} + 1.25 \times \text{ED}$.
  * In `OxygenDashboard.jsx`: Capacity = 60 Cylinders; formula = $1.5 \times \text{ICU}$.
* **Blood Discrepancy:**
  * In `multi_resource.py`: Derived from ED arrivals ($0.20 \times \text{ED}$); capacity = 10.0 units.
  * In `BloodDashboard.jsx`: Derived from ICU beds ($0.80 \times \text{ICU}$); capacity = 200 units.
* **Staff Discrepancy:**
  * In `multi_resource.py`: Formula = $1.5 \times \text{ICU} + 0.125 \times \text{ED}$; capacity = 12.0 FTE.
  * In `StaffDashboard.jsx`: Formula = $1.2 \times \text{ICU} + 0.4 \times \text{ED}$; capacity = 110 staff pool.
* **Ambulance Discrepancy:**
  * In `multi_resource.py`: Formula = $0.15 \times \text{ED}$; capacity = 5.0 Cars.
  * In `AmbulanceDashboard.jsx`: Formula = $\lceil \text{ED} / 6 \rceil$; capacity = 12 ambulances.

---

## 6. Confirmed Defects Categorization

### High Severity
* **[DEFECT-H1] Inconsistent Formula and Capacity Definitions Across Frontend and Backend:**
  * **Location:** `backend/routers/multi_resource.py` vs. `frontend/src/pages/{OxygenDashboard,BloodDashboard,StaffDashboard,AmbulanceDashboard}.jsx`.
  * **Evidence:** In `multi_resource.py`, Blood is derived from ED arrivals ($0.20 \times \text{ED}$, capacity 10). In `BloodDashboard.jsx`, Blood is derived from ICU beds ($0.80 \times \text{ICU}$, capacity 200). Oxygen uses Liters (cap 100) in the multi-resource API but Cylinders (cap 60) in the dedicated tab.
  * **Recommended Fix:** Unify the heuristic conversion rules in a single shared configuration module or backend service, ensuring identical capacities and formulas across all views.
* **[DEFECT-H2] Hardcoded Static Mockup Array in General Beds Dashboard:**
  * **Location:** `frontend/src/pages/BedsDashboard.jsx` lines 70–77.
  * **Evidence:** General Beds tab renders a hardcoded array `[78, 80, 83, 88, 84, 80, 79]` with hardcoded capacity 150, ignoring backend API data.
  * **Recommended Fix:** Connect `BedsDashboard.jsx` for General Beds to the `/api/forecast/multi` endpoint so it renders the dynamic backend projection.

### Medium Severity
* **[DEFECT-M1] Cross-Century Date Pairing in Multi-Resource Endpoint:**
  * **Location:** `backend/routers/multi_resource.py` lines 186–189.
  * **Evidence:** The loop couples October 2137 ICU forecasts with January 2148 ED forecasts by array index, labeling the resulting multi-resource forecast with year 2137 dates.
  * **Recommended Fix:** Document explicitly in API responses and UI that ICU and ED forecasts are aligned by ordinal forecast step ($h = 1 \dots 7$) rather than synchronized calendar timestamps.
* **[DEFECT-M2] Generic "units" Label and Unconditional Ceiling in AlertTable:**
  * **Location:** `frontend/src/components/AlertTable.jsx` lines 148–162.
  * **Evidence:** Oxygen and Staff are rendered with `"units"` suffix and continuous values are ceiling-rounded.
  * **Recommended Fix:** Pass resource units dynamically from `RESOURCE_METADATA` into `AlertTable.jsx`, and apply integer ceiling only to discrete count assets.
* **[DEFECT-M3] Complete Architectural Decoupling of California Research from Web Dashboard:**
  * **Location:** `ml/forecasting/california_*.py` vs `backend/routers/*`.
  * **Evidence:** The California statewide dataset is only executed via standalone research scripts. The live dashboard communicates strictly with MIMIC-IV and simulated endpoints.
  * **Recommended Fix:** Add a dedicated "Academic Research & Statewide Census" view in the dashboard or document the dual-track architecture in the system overview.

### Low / Informational
* **[DEFECT-L1] Orphaned Demo Dataset File:**
  * **Location:** `data/raw/external/hri_complete_demo_daily.csv`.
  * **Evidence:** File exists on disk but is unreferenced in all Python and JavaScript code.
  * **Recommended Fix:** Archive or remove the orphaned file to avoid developer confusion.
* **[DEFECT-L2] Unused NHS Beds Processed Dataset in Backend:**
  * **Location:** `data/processed/beds_monthly_processed.csv`.
  * **Evidence:** Generated from NHS England publication but never loaded into database.
  * **Recommended Fix:** Clarify in `DATA_DICTIONARY.md` that the NHS dataset serves exploratory feature benchmarking only.
* **[DEFECT-I1] 22nd Century Dates Visible in UI:**
  * **Location:** `frontend/src/pages/Dashboard.jsx`.
  * **Evidence:** Calendar dates displayed in the UI fall in the year 2137.
  * **Recommended Fix:** Add a tooltip or badge explaining that dates reflect MIMIC-IV de-identified privacy offsets.

---

## 7. Recommended Fixes Ordered by Priority

1. **Priority 1 (Formulation Alignment):** Align dedicated resource dashboards (`OxygenDashboard`, `BloodDashboard`, `StaffDashboard`, `AmbulanceDashboard`) to use the exact formulas, capacities, and units defined in `backend/routers/multi_resource.py`.
2. **Priority 2 (Eliminate Hardcoded UI Mockup):** Replace the static mockup array in `BedsDashboard.jsx` (General Beds) with dynamic data fetched from `apiService.getMultiResourceForecast()`.
3. **Priority 3 (Unit-Aware Alert Rendering):** Update `AlertTable.jsx` to render resource-appropriate unit labels ("Beds", "Liters", "Units", "FTE", "Vehicles") and avoid rounding continuous liter quantities.
4. **Priority 4 (MIMIC-IV Date Offset Disclosure):** Add an informative UI badge on the dashboard clarifying that calendar years in the 2100s represent standardized MIMIC-IV HIPAA de-identification offsets.
5. **Priority 5 (Documentation & Asset Cleanup):** Update `DATA_DICTIONARY.md` to note that `hri_complete_demo_daily.csv` is an unlinked demo artifact, and clarify the dual-track relationship between California statewide research and the operational demonstration dashboard.

---

## 8. Concrete Audit Evidence

* **Automated Test Results (All 75 Passing):**
  ```bash
  TESTING=True pytest
  # Output: 75 passed, 65 warnings in 13.70s
  ```
* **Validation Scripts (All 10 Passing):**
  * `python3 tests/test_end_to_end.py` $\rightarrow$ ALL END-TO-END INTEGRATION TESTS PASSED
  * `python3 tests/validate_database_schema.py` $\rightarrow$ ALL TESTS PASSED
  * `python3 tests/validate_features.py` $\rightarrow$ VALIDATED
  * `python3 tests/validate_lstm.py` $\rightarrow$ VALIDATED
  * `python3 tests/validate_model_comparison.py` $\rightarrow$ VALIDATED
  * `python3 tests/validate_processed_data.py` $\rightarrow$ VALIDATED
  * `python3 tests/validate_prophet.py` $\rightarrow$ VALIDATED
  * `python3 tests/validate_shortage_engine.py` $\rightarrow$ OK (8 tests passed)
  * `python3 tests/validate_xai.py` $\rightarrow$ VALIDATED
  * `python3 tests/validate_xgboost.py` $\rightarrow$ VALIDATED
* **California Rolling-Origin Outputs Verified Intact:**
  * JSON: `outputs/rolling_evaluation/rolling_experiment_metrics.json` (4,217 bytes)
  * Detailed Predictions: `outputs/rolling_evaluation/rolling_forecast_predictions.csv` (64,407 bytes, 1,092 predictions)
  * Horizon Breakdown: `outputs/rolling_evaluation/rolling_horizon_metrics.csv` (741 bytes)
  * Summary: `outputs/rolling_evaluation/rolling_origin_summary.csv` (6,443 bytes)
  * Visual Benchmark: `outputs/rolling_evaluation/rolling_horizon_comparison.png` (411,473 bytes)
* **Live Server Diagnostic Responses:**
  * `GET /health` $\rightarrow$ `HTTP 200` `{"status":"healthy","database":"healthy"}`
  * Header: `X-Clinical-Notice: Operational metrics only. Systems must not be used for diagnosis or patient treatment decisions`
  * `GET /api/model-performance` $\rightarrow$ `HTTP 200` (6 metrics records)
  * `GET /api/forecast/multi` $\rightarrow$ `HTTP 200` (7 resource entries)

---

## 9. Separation of Verified Facts, Inferred Behavior, and Unverified Claims

### Verified Facts
* `california_hospital_capacity_daily.csv` contains 1,544 rows of real, statewide aggregate data for California acute-care facilities from Feb 2020 through Apr 2024.
* The 52-week rolling-origin experiment (`california_rolling_origin_experiment.py`) is mathematically sound, respects chronology, prevents leakage, and reproduces the single-holdout results at Origin 52.
* The database `historical_demand` table contains only 360 rows: 180 rows for ICU Beds and 180 rows for ED Arrivals.
* Resources 3 through 7 (General Beds, Oxygen, Blood, Staff, Ambulances) have no independently trained ML models in the codebase; they are heuristic functions of ICU and ED outputs.
* All 75 automated pytest unit tests pass cleanly in the monolithic test run.

### Inferred Behavior
* MIMIC-IV date shifts were introduced to comply with HIPAA Safe Harbor de-identification rules, explaining the 22nd-century dates (2110–2201).
* The discrepancy between formulas in dedicated dashboard tabs and the multi-resource API stems from parallel development of the resource dashboards and the unified multi-resource endpoint.

### Unverified Claims
* Any claim that all 7 resource categories have been empirically evaluated against real-world hospital telemetry is **UNVERIFIED and FALSE** (only ICU and ED have models evaluated against holdout actuals).
* Docker deployment capability in the host environment is **UNVERIFIED** (Docker runtime is not installed on the system).

---

## 10. Final Readiness Checklist

### Ready for Software Demonstration
- [x] Complete web application startup (FastAPI on 8000 + React on 5173).
- [x] Role-Based Access Control (Admin, Planner, Viewer login, session persistence, CRUD restrictions).
- [x] CSV dataset upload and validation engine with error reporting.
- [x] Manual resource record entry with immediate reflection in Data Management History.
- [x] Multi-resource overview displaying 7 resources with simulated provenance tags.
- [x] Decision engine alert generation with configurable capacity safeguards.
- [x] Local explainability (SHAP & LIME contribution bar charts).
- [x] Model comparison dashboard displaying MAE and RMSE rankings across XGBoost, Prophet, and LSTM.

### Supported for Academic Research Claims
- [x] California statewide inpatient bed forecasting on 1,544 daily observations (Feb 2020 – Apr 2024).
- [x] Leakage-free 7-day single-holdout evaluation (Ridge MAE 1,000.00 vs. Seasonal Naive MAE 1,154.29).
- [x] Reproducible 52-week rolling-origin evaluation across 364 evaluated days (XGBoost MAE 639.26, MASE 0.5072).
- [x] Horizon-specific breakdown of recursive error compounding across Steps 1 to 7.
- [x] Disclosed limitations regarding statewide macro-aggregation and static capacity assumptions.

### Not Supported / Unverified for Real Clinical Practice
- [ ] Direct clinical decision support or individual hospital capacity management (MIMIC-IV unit sparsity and statewide macro-aggregation prevent facility-specific deployment).
- [ ] Machine-learning validation for General Beds, Oxygen, Blood, Staff, and Ambulance (formula-derived heuristics only).
- [ ] Docker containerized orchestration on the current host machine (Docker CLI not installed).
