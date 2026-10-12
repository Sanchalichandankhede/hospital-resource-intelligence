# Production-Ready Deployment Manual

This document provides system administration instructions for configuring, building, running, and troubleshooting the Hospital Resource Forecasting and Capacity Planning platform in a production-like environment.

---

## 1. System Architecture

The application is structured as a three-tier architecture:
1. **Frontend (Presentation Tier):** React/Vite SPA. In production, compiled static assets are served using Nginx (port `80`).
2. **Backend (Application Tier):** FastAPI REST server. Runs in a production configuration using Uvicorn (port `8000`).
3. **Database (Data Tier):** PostgreSQL relational database management system (port `5432`).

### Production Data Flow
* The user interacts with the **React Dashboard** in their browser.
* The frontend makes REST API fetches to the **FastAPI Backend** (configured via `VITE_API_BASE_URL`).
* The backend queries forecast predictions, alerts, and explanations from the **PostgreSQL Database** using parameterized transactions.
* **Testing Mode Isolation:** When `TESTING=True` is defined in the system environments, the backend bypasses PostgreSQL entirely and connects to a localized workspace SQLite connection (`sqlite:///test.db`) to enable standalone route checks.

---

## 2. Prerequisites

To run this platform in production, the host environment must have the following installed:
* **Operating System:** Linux (Ubuntu 22.04+ recommended), macOS, or Windows (via WSL2).
* **Docker Engine:** Version 24.0.0+ and **Docker Compose** v2.20.0+.
* **Python:** Version 3.12 (if executing bare-metal installations).
* **Node.js:** Version 20 (if building static client assets manually).

---

## 3. Environment Variables

The application is configured using a `.env` file placed in the project root. Refer to [`.env.example`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/.env.example) for placeholder values.

| Variable Name | Required | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `TESTING` | Yes | `False` | Set to `False` to use production PostgreSQL. Set to `True` for SQLite fallback. |
| `DB_HOST` | Yes | `localhost` | Network hostname of the PostgreSQL database server. |
| `DB_PORT` | Yes | `5432` | Network port of the PostgreSQL database server. |
| `DB_NAME` | Yes | `hospital_resource_intelligence` | Database schema name. |
| `DB_USER` | Yes | `postgres` | Database admin username. |
| `DB_PASSWORD` | Yes | N/A | Database password (do not leave empty or default in production). |
| `CORS_ORIGINS` | Yes | `["http://localhost:80"]` | JSON array of allowed origins for browser security. |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | URL location of the FastAPI backend, consumed by the React app. |

---

## 4. Docker Deployment Setup (Recommended)

Docker Compose coordinates the database, application server, and web client automatically.

### Step 1: Clone and Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in secure passwords for `DB_PASSWORD`.

### Step 2: Build and Launch Containers
Execute the Docker Compose builder:
```bash
docker compose up --build -d
```
This command builds the backend and Nginx-compiled frontend images and launches them in detached mode.

### Step 3: Run Database Migrations and Seed Data
Once the database container is online, initialize the schema DDL and load the ML outputs into PostgreSQL:
```bash
docker compose exec backend python3 database/load_data.py
```
This executes the database loader inside the backend container context against the production PostgreSQL instance.

---

## 5. Manual Local Production Setup (Bare-Metal)

If you prefer to run the services bare-metal without Docker:

### A. Database Initialization
1. Ensure a PostgreSQL instance is running on port `5432`.
2. Connect to postgres CLI and create the database:
   ```sql
   CREATE DATABASE hospital_resource_intelligence;
   ```
3. Load the schema DDL definitions:
   ```bash
   psql -h localhost -U postgres -d hospital_resource_intelligence -f database/schema.sql
   ```

### B. Backend Production Startup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure `.env` in the root (set `TESTING=False` and fill database variables).
3. Start the production FastAPI server using Uvicorn:
   ```bash
   PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

### C. Frontend Production Build & Run
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm modules:
   ```bash
   npm install
   ```
3. Copy environment config:
   ```bash
   cp .env.example .env
   ```
4. Build production files:
   ```bash
   npm run build
   ```
5. Serve the generated assets using a web server or locally via Vite preview for testing:
   ```bash
   npm run preview -- --port 80
   ```

---

## 6. Health Checks & Verification

Confirm that all services are communicating correctly:

### 1. API Health Diagnostic
Query the health endpoint from the command-line:
```bash
curl -i http://localhost:8000/health
```
**Expected Response:**
```json
HTTP/1.1 200 OK
content-type: application/json
X-Clinical-Notice: Operational metrics only. Systems must not be used for diagnosis or patient treatment decisions

{"status":"healthy","database":"healthy"}
```

### 2. Verify Forecasts Payload
Query active forecast points:
```bash
curl -i "http://localhost:8000/api/forecast/icu?model=XGBoost"
```
Ensure it returns a populated predictions list with valid date targets.

---

## 7. Troubleshooting

* **Frontend Shows "Connection Error" overlay:**
  - Verify that the FastAPI backend container is running (`docker compose ps`).
  - Open browser inspection tools and check console logs. If a CORS fetch error is logged, verify that the frontend's origin URL is added to the `CORS_ORIGINS` JSON array in `.env`.
* **Database Connection Failures on Backend:**
  - Verify that PostgreSQL is online.
  - If running bare-metal, ensure postgres configurations (`pg_hba.conf`) allow connections from localhost.
* **Database Schema Mismatch or Empty Tables:**
  - Re-run the data seeder script: `PYTHONPATH=. TESTING=False python3 database/load_data.py`.

---

## 8. Security Considerations

* **Disable Debug Logs:** Never run backend commands in production with the `--reload` flag enabled.
* **Isolate Secrets:** Never hard-code database credentials in the application files. Maintain them strictly inside the host environment or `.env` files which are excluded from Git.
* **CORS Restrictions:** Avoid using wildcards (`"*"`) for `CORS_ORIGINS` in production. Only specify valid client web addresses.
* **Clinical Safety Header:** Ensure the custom header middleware remains active on the main app router to enforce analytical limitations warning flags on all response payloads.

---

## 9. Prototype Limitations

1. **Simulated Capacity limits:** Bed caps are demonstration benchmarks (e.g. ICU capacity is set to `2.0` beds). Warnings are displayed next to capacity fields on the dashboard alerts panel.
2. **Correlation vs Causation:** SHAP/LIME feature attributions represent statistical model weights and do **not** imply biological or operational causation.
3. **Small Sample Scope:** The models are trained on small anonymized historical telemetry.
