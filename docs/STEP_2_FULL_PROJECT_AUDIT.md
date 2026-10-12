# Step 2: Full Project Audit Report (Stages 1 to 15)

This report details the project-wide audit conducted on the **Hospital Resource Intelligence Platform**, examining data pipelines, machine learning models, database architecture, APIs, frontend UI pages, and deployment containers.

---

## 1. Project Structure

### Important Folders and Files

```
├── backend/
│   ├── main.py (FastAPI entrypoint)
│   ├── config.py (Config environment mappings)
│   ├── database.py (SQLAlchemy DB Engine connection wrapper)
│   ├── Dockerfile (Backend containerization)
│   ├── models/db_models.py (SQLAlchemy Schema mapping declarations)
│   └── routers/ (forecast.py, explanations.py, alerts.py, recommendations.py, performance.py, multi_resource.py)
├── frontend/
│   ├── Dockerfile & nginx.conf (Frontend client deployment containers)
│   ├── package.json & vite.config.js (Vite environment configurations)
│   └── src/
│       ├── main.jsx & App.jsx (React entrypoints)
│       └── components/ (MultiResourceForecasting.jsx, ExplanationChart.jsx, ModelComparison.jsx, AlertTable.jsx)
├── database/
│   ├── schema.sql (PostgreSQL DDL script)
│   └── load_data.py (SQLite DB seeding routine)
├── data/
│   ├── raw/ (Raw target source tables: icu_daily_demand.csv, ed_daily_demand.csv, Beds...xlsx)
│   ├── processed/ (Preprocessed calendar demand features)
│   └── interim/ (Saved XGBoost, Prophet, and LSTM 7-day model outputs)
├── ml/
│   ├── preprocessing/cleaning.py (Data cleaning routines)
│   ├── features/generator.py (Time-series lag generator)
│   ├── forecasting/ (XGBoost, Prophet, and PyTorch LSTM models scripts)
│   ├── evaluation/compare.py (Errors comparator metric sheets)
│   ├── explainability/ (SHAP and LIME coefficient calculators)
│   └── decision_engine/ (Shortage detectors, alert mappings, and thresholds)
├── outputs/ (alerts/, explainability/, recommendations/)
├── tests/ (test_api.py, test_end_to_end.py, and validate_*.py scripts)
├── docs/ (academic documentation and design specifications)
└── docker-compose.yml (Coordinator of frontend, backend, and DB services)
```

* **Missing Files:** None.
* **Unused/Obsolete Files:** None.

---

## 2. Dataset / Data Provenance

### Dataset Catalog

* **`icu_daily_processed.csv`**
  - **Location:** `data/processed/`
  - **Rows:** 180 | **Columns:** 2 (`date`, `occupied_beds`)
  - **Date Range:** `2137-04-21` to `2137-10-17`
  - **Target Variable:** `occupied_beds` (occupied ICU beds count)
  - **Duplicates/Missing:** None
  - **Provenance:** **REAL / SOURCE-DERIVED**
* **`ed_daily_processed.csv`**
  - **Location:** `data/processed/`
  - **Rows:** 180 | **Columns:** 2 (`date`, `arrivals`)
  - **Date Range:** `2147-07-30` to `2148-01-25`
  - **Target Variable:** `arrivals` (daily arrivals count)
  - **Duplicates/Missing:** None
  - **Provenance:** **REAL / SOURCE-DERIVED**
* **`beds_monthly_processed.csv`**
  - **Location:** `data/processed/`
  - **Rows:** 76 | **Columns:** 37
  - **Date Range:** `2020-12-01` to `2027-03-01`
  - **Target Variable:** various monthly NHS bed counts.
  - **Duplicates/Missing:** None
  - **Provenance:** **REAL / SOURCE-DERIVED** (from UK NHS publication Excel tables)

### Resource Support Assessment

The raw/processed datasets in the workspace only contain actual observations for **ICU Demand** and **ED Arrivals**. The remaining five resource categories do not have direct telemetry and are derived using planning assumptions.

* **ICU Demand:** **REAL / SOURCE-DERIVED**
* **General Bed Demand:** **SIMULATED / DERIVED** (derived from ICU beds)
* **Emergency Bed Demand:** **SIMULATED / DERIVED** (derived from ED arrivals)
* **Oxygen Demand:** **SIMULATED / DERIVED** (derived from ICU + Emergency beds)
* **Blood Demand:** **SIMULATED / DERIVED** (derived from ED arrivals)
* **Staff Requirement:** **SIMULATED / DERIVED** (derived from ICU + Emergency beds)
* **Ambulance Requirement:** **SIMULATED / DERIVED** (derived from ED arrivals)

---

## 3. Machine Learning Pipeline

### Preprocessing & Features
* **Cleaning:** `cleaning.py` reindexes event logs to a full daily calendar, fills gaps with 0, and extracts the densest 180-day window.
* **Leakage Prevention:** Rolling statistics in `generator.py` shift inputs by 1 day (`shift(1)`) to eliminate target leakage.
* **Splitting:** Aligned strictly to `7 days` test window split chronologically:
  - **Training:** Days 1-173
  - **Testing:** Days 174-180
* **XGBoost Superiority:** XGBoost beats Prophet and LSTM in ICU prediction metrics (ICU MAE: 0.5940 vs. 0.6198 for Prophet vs. 0.7164 for LSTM). For ED Arrivals, XGBoost has the best MAE (0.2891), making it the optimal operational model for average error reduction.

---

## 4. Explainable AI (XAI)

* **Implementations:** Kernel SHAP and LIME Tabular explainer models are fit strictly on XGBoost parameters.
* **Scope:** Local attributions explain the final day of the test window (`2137-10-17` for ICU, `2148-01-25` for ED).
* **Logical Consistency:** Attributions correspond strictly to model training input features.
* **Disclaimer:** `XAI_METHODOLOGY.md` contains a warning stating that SHAP/LIME coefficients represent **associations** within the model, not clinical causality.

---

## 5. Shortage & Recommendation Engine

* **Shortages:** Calculated on operational whole numbers: `Shortage = max(0, Operational Requirement - Available Capacity)`.
* **Risk Levels:** Evaluated on the operational gap. Maps alerts to standard levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
* **Clinical Safety:** Mapped alerts trigger administrative suggestions (e.g. "Review bed availability") and never advise clinical diagnostic paths.

---

## 6. Multi-Resource Forecasting Formulation

Calculations from `backend/routers/multi_resource.py`:

| Target Resource | Unit | Provenance | Ground Truth? | Formula / Multiplier | Metric Safety |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **1. ICU Demand** | Beds | Real | **Yes** | $pred = icu\_val$ | Display metrics |
| **2. General Beds** | Beds | Sim | No | $pred = 18.0 + (icu\_val \times 2.0)$ | Mute metrics (`None`) |
| **3. Emergency Beds** | Beds | Sim | No | $pred = ed\_val \times 0.25$ | Mute metrics (`None`) |
| **4. Oxygen Demand** | Liters | Sim | No | $pred = (icu\_val \times 15.0) + (ed\_val \times 0.25 \times 5.0)$ | Mute metrics (`None`) |
| **5. Blood Demand** | Units | Sim | No | $pred = ed\_val \times 0.20$ | Mute metrics (`None`) |
| **6. Staffing** | FTE / staff | Sim | No | $pred = (icu\_val \times 1.5) + (ed\_val \times 0.25 \times 0.5)$ | Mute metrics (`None`) |
| **7. Ambulances** | Cars | Sim | No | $pred = ed\_val \times 0.15$ | Mute metrics (`None`) |

---

## 7. Operational Quantization

For discrete targets, continuous forecasts ($f_{raw}$) are mapped into integers using ceiling rounding, with safe zero handling:

$$R_{op} = \begin{cases} 0 & \text{if } f_{raw} \le 0 \\ \lceil f_{raw} \rceil & \text{if } f_{raw} > 0 \end{cases}$$

* **Oxygen Exception:** Kept continuous (float) in Liters.
* **Separation:** Raw predicted values are preserved separately from operational requirements, satisfying model evaluation safety.

---

## 8. Database

* **Tables:** Schema establishes 7 tables (`historical_demand`, `forecasts`, `model_performance`, `alerts`, `recommendations`, `explanations`, `model_metadata`).
* **Constraints:** Primary keys, foreign keys, unique indices, and indexes are identical between SQLAlchemy models and the production DDL script.
* **Seeding:** The SQLite seeding routine (`load_data.py`) imports values matching the CSVs.

---

## 9. FastAPI Backend

* **Endpoints:** Exposes `/api/forecast/icu`, `/api/forecast/ed`, `/api/alerts`, `/api/recommendations`, `/api/explanations/icu`, `/api/explanations/ed`, `/api/model-performance`, and `/api/forecast/multi`.
* **Headers:** Adds `X-Clinical-Notice` safety header on all HTTP responses.
* **Validation:** ISO date formats are parsed, returning `HTTP 400` on formatting errors.

---

## 10. React Frontend

* **Terminologies:** Clearly splits **Raw ML Forecast** from **Operational Requirement** in visual cards.
* **Bespoke Tables & Charts:** Renders 7-day grid tables and step lines mapping quantized requirements against capacities.
* **Disclaimers:** Displays warnings on all simulated resource cards and explains ceiling math on the XAI page.

---

## 11. Deployment

* **Architecture:** Coordinates PostgreSQL, backend, and static Nginx client hosting.
* **Container configuration:** `docker-compose.yml` passes env vars (`TESTING=False` to trigger PostgreSQL connectivity).

---

## 12. Testing

The verification scripts in `tests/` were executed:

1. **Route unit tests (`pytest tests/test_api.py`):**
   - **Passed:** 11 | **Failed:** 0
2. **Integration verification suite (`python3 tests/test_end_to_end.py`):**
   - **Passed:** 10 validation stages (seeding, matches, gaps, quantization) | **Failed:** 0
3. **Database Schema check (`python3 tests/validate_database_schema.py`):**
   - **Passed:** PK, FK, index rules | **Failed:** **1** (Checks Alerts constraint)

---

## 13. Mathematical & Logical Consistency

1. **Date Range Discrepancy:** The raw datasets are disjoint (ICU timeline is in 2137, while ED arrivals timeline is in 2147). The multi-resource forecasting router aligns them by forecast index `i` rather than calendar date to allow comparative calculations.
2. **Alerts Schema Constraint Inconsistency:** `validate_database_schema.py` expects risk level check constraints to strictly contain `('low', 'medium', 'high')` from Stage 10A, but `schema.sql` was correctly expanded in Stage 13 to support `CRITICAL` (e.g. `IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')`).
3. **Low-count sparse event data:** Daily ICU Bed occupied and ED Arrivals are highly sparse (80%+ zeros). Because of this sparsity, model regression predictions are extremely small fractional expectations (e.g. `0.01` arrivals), which then correctly round up to `1` unit for physical resources (blood, staff, ambulances).

---

## 14. Academic & Research Quality

The platform is mathematically and operationally defensible for academic presentation.
* **Strengths:** Separation of expectations (raw continuous forecasts) from physical allocations (operational requirements); clear data classification badges (`REAL / SOURCE-DERIVED` vs. `SIMULATED / PROTOTYPE`).
* **Weaknesses/Limitations (to acknowledge during Viva):** Linear multiplier resource multipliers are simplified prototype assumptions; training data size (180 days) is small, meaning model feature weights are descriptive rather than universal facility guidelines.

---

## 15. Final Audit Summary

| Area | Status | Severity | Finding | Recommended Action |
| :--- | :--- | :--- | :--- | :--- |
| **Dataset / Data Provenance** | **WARNING** | **LOW** | ICU (2137) and ED (2147) dates are 10 years apart, necessitating index-based alignment. | Acknowledge date alignment in the presentation. |
| **ML Pipeline** | **PASS** | **LOW** | Model splits are chronological and prevent target leakage. | Already correct. |
| **Explainable AI (XAI)** | **PASS** | **LOW** | Attributions explain raw predictions; has causality warning. | Already correct. |
| **Shortage & Rec Engine** | **PASS** | **LOW** | Shortages are based on whole numbers and recommendations are non-clinical. | Already correct. |
| **Multi-Resource Formulations** | **PASS** | **LOW** | Dynamic formulas are linear approximations of patient load multipliers. | Already correct. |
| **Operational Quantization** | **PASS** | **LOW** | Ceil rounds discrete items; Oxygen remains continuous. | Already correct. |
| **Database** | **PASS** | **LOW** | Schema has 7 tables with matching models. | Already correct. |
| **FASTAPI Backend** | **WARNING** | **LOW** | `/api/alerts` endpoint validation does not allow querying `"CRITICAL"` risk level parameter. | *(Optional)* Expand endpoint risk parameters to allow `"CRITICAL"`. |
| **React Frontend** | **PASS** | **LOW** | Frontend separates raw forecasts from operational requirements. | Already correct. |
| **Deployment** | **PASS** | **LOW** | Docker compose coordinates static client build and backend database. | Already correct. |
| **Testing** | **WARNING** | **LOW** | `validate_database_schema.py` fails check constraints because it expects the old constraint without `"CRITICAL"`. | Update test script to match the expanded check constraint. |

---

### A. What is Genuinely Complete
* **Machine Learning Pipelines:** Prophet, XGBoost, and LSTM models fit, evaluate, and save forecasts.
* **Database & APIs:** Normalized SQLite database seeded with actual matching records; FastAPI routes return compliant payloads with custom headers.
* **React Dashboard:** Multi-resource cards, step line graphs, 7-day grids, model comparators, and SHAP/LIME charts.

### B. What is Partially Implemented
* **Alert risk level query parameter filter:** `/api/alerts` checks risk levels but is missing `"CRITICAL"` in the accepted parameter list.

### C. What is Simulated / Assumption-Based
* **Secondary targets:** General Beds, Emergency Beds, Oxygen, Blood, Staff, and Ambulance demand calculations are calculated using deterministic linear patient load multipliers.

### D. What MUST be Fixed Before Final Submission
* Update the database schema test `validate_database_schema.py` to recognize the expanded check constraint containing `'CRITICAL'`.

### E. What SHOULD be Improved If Time Permits
* Modify `/api/alerts` endpoint risk level check list to permit `"CRITICAL"` filters.

### F. What should NOT be Changed
* **Model pipelines and database schema:** Model splits, training inputs, and database schemas are correct and must not be retrained or modified.
