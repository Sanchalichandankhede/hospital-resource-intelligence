# Backend Implementation Reference Document

This document describes the FastAPI backend implementation, configuration, database connectivity, router endpoints, security models, and local startup instructions.

---

## 1. Directory Structure

The backend code is organized modularly under the `backend/` folder:

```
backend/
├── main.py                # FastAPI entry point & middleware configurations
├── database.py            # SQLAlchemy Engine and get_db session dependency
├── config.py              # Configuration manager for environment parameters
├── models/
│   ├── __init__.py        # Export class interfaces
│   └── db_models.py       # SQLAlchemy ORM models matching database schema
├── schemas/
│   ├── __init__.py        # Export Pydantic models
│   └── models.py          # Pydantic request/response validation schemas
└── routers/
    ├── __init__.py        # Routers export
    ├── forecast.py        # /api/forecast/icu and /api/forecast/ed routes
    ├── alerts.py          # /api/alerts route
    ├── recommendations.py # /api/recommendations route
    ├── explanations.py   # /api/explanations/icu and /api/explanations/ed routes
    └── performance.py     # /api/model-performance comparison metrics route
```

---

## 2. Configuration & Database Connectivity

### A. Environment Configuration
Variables are read from system environments or a local `.env` file via `python-dotenv`:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: Database credentials.
- `API_PORT`: Target port (defaults to `8000`).
- `CORS_ORIGINS`: JSON array of allowed origins (defaults to `["http://localhost:3000"]`).

### B. SQLAlchemy Engine Connection
Implemented in [`database.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/database.py). 
* **Dialect Portability:** If `TESTING=True` is defined in the system environments, the connection automatically routes to an SQLite database file (`test.db`), which is populated by the loader script and destroyed upon test suite completion.
* In production, the session maker routes commands to PostgreSQL using `psycopg2-binary`.

---

## 3. Implemented API Endpoints

### A. GET `/health`
* **Description:** Performs server diagnostic checks and a database query verification (`SELECT 1`).
* **Response:**
  ```json
  {
    "status": "healthy",
    "database": "healthy"
  }
  ```

### B. GET `/api/forecast/icu` and GET `/api/forecast/ed`
* **Description:** Fetches predictions from the target resource's forecasting model (defaults to `'XGBoost'`).
* **Parameters:**
  - `start_date` (optional string): ISO format YYYY-MM-DD.
  - `end_date` (optional string): ISO format YYYY-MM-DD.
  - `model` (optional string): Defaults to `'XGBoost'`.
* **Validation:** Rejects invalid date formats or if `start_date > end_date` with `400 Bad Request`.

### C. GET `/api/alerts`
* **Description:** Lists generated resource shortage risks.
* **Parameters:** `resource` (filter string), `risk_level` (LOW, MEDIUM, HIGH), `start_date`, `end_date`.
* **Disclaimers:** Every alert response enforces safety markers:
  ```json
  {
    "date": "2137-10-11",
    "resource": "ICU Beds",
    "predicted_demand": 0.2041,
    "actual_capacity": null,
    "simulated_capacity": 2.0,
    "is_capacity_simulated": true,
    "capacity_gap": 1.7959,
    "risk_level": "LOW",
    "reason": "Predicted demand is within safe capacity bounds."
  }
  ```
  `actual_capacity` is set to `null` to represent dataset limitations, while `is_capacity_simulated` is set to `true`.

### D. GET `/api/recommendations`
* **Description:** Lists operational tasks triggered by risk thresholds. Joins recommendation rows against the parent alert ID.

### E. GET `/api/explanations/icu` and GET `/api/explanations/ed`
* **Description:** Returns local feature contributions for the specified forecast date.
* **Parameters:** `date` (ISO format string), `method` (defaults to `'SHAP'`, options: `'SHAP'` / `'LIME'`).

### F. GET `/api/model-performance`
* **Description:** Returns aggregated MAE, RMSE, and MAPE scores comparing Prophet, XGBoost, and LSTM forecasting runs.

---

## 4. Security & Safety Safeguards

1. **Parameter Sanitization:** Parameters are parsed through ORM objects or parameterized values (`%s`) preventing SQL injection exploits.
2. **Clinical Safety Header:** Every response automatically appends a safety disclaiming header:
   `X-Clinical-Notice: Operational metrics only. Systems must not be used for diagnosis or patient treatment decisions`
3. **Pydantic Validation:** Inputs are validated via Pydantic model configurations.
4. **CORS Whitelisting:** Configures Middleware CORS explicitly via `CORS_ORIGINS` to permit only whitelisted domains.

---

## 5. Startup Instructions

To start the backend server locally:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Configure credentials in `.env` if using PostgreSQL.
3. Install dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv pydantic pytest
   ```
4. Seed historical and forecast outputs:
   ```bash
   python3 database/load_data.py
   ```
5. Run the Uvicorn development server:
   ```bash
   uvicorn backend.main:app --reload
   ```
   The API interactive docs will be available at `http://localhost:8000/docs`.
