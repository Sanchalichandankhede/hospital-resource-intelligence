# Integration and End-to-End System Test Report

This document records the end-to-end integration verifications, security audits, performance checklists, and known limits of the Hospital Resource Forecasting and Capacity Planning system.

---

## 1. System Integration Test Matrix

All verifications below were evaluated using automated integration suites ([`test_end_to_end.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/tests/test_end_to_end.py) and [`test_api.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/tests/test_api.py)) and browser audit recordings.

| Test Case ID | Target Component | Description / Actions | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IT-01** | Database Schema | Verify tables, constraints, indexes DDL structure. | 7 tables created with keys/indexes. | All tables and foreign keys successfully initialized. | **PASS** |
| **IT-02** | Data Seeder | Load output files into DB. | Seeding completes without error. | Database seeded with 360 demand records. | **PASS** |
| **IT-03** | Forecast Integrity | Compare `outputs/` CSV vs DB vs API. | Match target values to within 1e-4. | ICU 2137-10-11 prediction matches 0.2041. | **PASS** |
| **IT-04** | Capacity Separation | Verify actual vs simulated capacities. | `is_capacity_simulated = TRUE`, `actual_capacity = NULL`. | Capacity types correctly distinguished. | **PASS** |
| **IT-05** | Alerts & Warnings | Verify API response includes simulated flags. | Correct flags returned to client. | API returns `is_capacity_simulated=True` for alerts. | **PASS** |
| **IT-06** | Recommendations | Check advice corresponds to target resource/date. | Recommendations map to correct trigger. | Admin logs successfully map to ICU/ED target dates. | **PASS** |
| **IT-07** | Explainable AI | Verify SHAP/LIME direction and weight vectors. | Positive/negative weights correctly exposed. | Feature `occupied_beds_lag_1` contribution matches 0.3098. | **PASS** |
| **IT-08** | Performance Metrics | Benchmark comparison dynamic winner selection. | Best model selected by minimum MAE. | XGBoost ranked #1 dynamically. | **PASS** |
| **IT-09** | API Route Suite | Query health checks and invalid ranges. | Health returns 200; invalid dates handle gracefully. | Empty and invalid parameters handled with 400 details. | **PASS** |
| **IT-10** | Frontend Nav | Click through navigation menu sidebar options. | Views swap dynamically. | Sidebar switches Overview/XAI/Performance tab states. | **PASS** |
| **IT-11** | CORS Configuration | Connect Vite port 5173 to FastAPI. | No CORS blockages in client browser. | Allowed origins updated to accept 5173 successfully. | **PASS** |
| **IT-12** | Connection Error | Stop backend and reload webpage. | Shows offline notice and Retry. | Error overlay renders correctly; Retry restores view. | **PASS** |

---

## 2. Browser Integration Audit Results

The browser subagent successfully completed a live check on `http://localhost:5173`. 
The full interaction sequence was saved to the recording file:
[`dashboard_verification_live_1787904598799.webp`](file:///Users/sanchalichandankhede/.gemini/antigravity-ide/brain/019a3e55-380d-4455-92cd-574137e638b6/dashboard_verification_live_1787904598799.webp)

### Observed Screen State Visuals
* **Overview:** Displays summary cards (ICU: `0.2 beds` / ED: `0.1 arrivals` / Risk: `LOW` / Horizon: `7 Days`) alongside active Recharts charts.
* **Forecasts:** Renders solid gray actual line and dashed blue predictions line. Model selection switches work.
* **Risk Alerts:** Displays interactive alerts list. Capacity limits are clearly tagged with: `⚠ Simulated Prototype`.
* **Recommendations:** Shows administrative capacity warnings. Contains strict non-clinical language notice.
* **Explainable AI:** Feature contribution bars fill correctly. Fills are color-coded (Blue for positive attributions, gray-slate for negative attributions).
* **Model Performance:** Renders Benchmarking comparison tables showing XGBoost, LSTM, and Prophet metrics (MAE, RMSE, MAPE).

---

## 3. Performance & Bottleneck Analysis
* **API Query Response Time:** Average API response time is `<15ms` for local SQLite queries.
* **Dashboard Initial Load:** The initial page load is completed in `<200ms` including assets bundle parsing.
* **Database Scaling:** The database indexes on `forecast_date`, `resource`, and `alert_date` ensure instant lookup times for 7-day windows.
* **Obvious Bottlenecks:** No obvious execution bottlenecks identified.

---

## 4. Security & Compliance Checklist
* **Credentials Isolation:** database credentials are fully isolated in environment variables.
* **Dotenv Setup:** The `.env` file is excluded from Git tracking via `.gitignore`.
* **SQL Parameterization:** Queries are compiled using SQLAlchemy ORM expressions, preventing SQL injection vulnerabilities.
* **CORS Settings:** Configured to restrict requests specifically to development origins (`http://localhost:3000`, `http://localhost:5173`, and `http://127.0.0.1:5173`).
* **Disclaimer Headers:** Backend responses include the `X-Clinical-Notice` custom disclaimer header:
  `"Operational metrics only. Systems must not be used for diagnosis or patient treatment decisions"`

---

## 5. System Limitations & Boundaries

### 1. Small Dataset Size
The project is built using a tiny anonymized prototype sample dataset. While the ML algorithms function correctly, model parameters must be retrained on full-scale hospital telemetry before deployment.

### 2. LSTM Performance Constraints
The deep-learning LSTM models are limited by the temporal context window of the small dataset size, meaning their current MAE is higher than XGBoost.

### 3. Simulated Capacity Limits
Physical hospital capacity parameters (e.g. ICU bed limits) are **not** present in the source files. These thresholds are simulated configurations (e.g., ICU capacity is fixed at `2.0` beds for low-alert verification).

### 4. Forecast Uncertainty
Predictive forecasts reflect statistical trends from historical sequences and do not account for external real-time events (e.g., mass casualty events, localized outbreaks).

### 5. SHAP/LIME Correlation vs. Causation
Feature importance contribution scores represent mathematical statistical association weights in the model and **do not** prove biological or logistical causation.

---

## 6. Final Status
* **Database status:** Healthy (All constraints and index rules passed).
* **Backend status:** Healthy (All unit tests and end-to-end tests passed).
* **Frontend status:** Healthy (Build succeeds, visual rendering validated).

**FINAL INTEGRATION SYSTEM STATUS:** **PASS**
