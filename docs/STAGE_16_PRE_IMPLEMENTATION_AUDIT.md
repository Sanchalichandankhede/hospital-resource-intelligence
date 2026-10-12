# Stage 16 Pre-Implementation Audit Report

This report outlines the technical characteristics of the existing platform before implementing the Stage 16 User Authentication and Data Management features.

---

## 1. Technical Frameworks and Versions

### A. Backend & Database
* **Database Engines:**
  - **Local/Test Development:** SQLite (`test.db` file) mapped dynamically when `TESTING=True`.
  - **Production/Deployment:** PostgreSQL 16 (configured via Environment parameters in `docker-compose.yml`).
* **SQLAlchemy Version / Style:**
  - SQLAlchemy `declarative_base()` is used to map schema classes to table attributes.
  - Model definitions reside in [`backend/models/db_models.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/models/db_models.py).
* **FastAPI Architecture:**
  - Modular routers registered in [`backend/main.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/main.py) routing requests to specific controller logic.
* **Pydantic version/style:**
  - Pydantic v2 (`model_validate` calls used for ORM conversion). Schemas defined in [`backend/schemas/models.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/schemas/models.py).

### B. Frontend
* **React version:** React 19 (`package.json` entry: `"react": "^19.2.8"`).
* **Routing/Navigation:**
  - Currently no `react-router-dom` dependency exists.
  - Page views are toggled dynamically inside [`Dashboard.jsx`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/frontend/src/pages/Dashboard.jsx) using the `activeSection` state variable.

### C. Authentication State
* **Current status:** None. All API routes are completely unprotected, and there are no users, passwords, or session tables.

---

## 2. API & Error Handling Conventions

* **API Conventions:**
  - Standard RESTful GET endpoints return JSON payloads matching Pydantic response models.
* **Error Handling:**
  - FastAPI `HTTPException` returns standard response details (e.g. `HTTP 400` on parsing issues, `HTTP 404` on missing records).
* **Clinical Notice Header:**
  - Middleware intercepts all HTTP routes to insert `X-Clinical-Notice: Operational metrics only...` in response headers.

---

## 3. Existing Environment Variables

Defined variables in `.env.example` and `backend/config.py`:
* `TESTING` (boolean flag to toggle SQLite test database fallback).
* `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (PostgreSQL binding specifications).
* `CORS_ORIGINS` (lists approved origins, whitelisting Vite dev ports).

---

## 4. Implementation Strategy

To implement user authentication and data management without breaking existing logic:
1. **User Authentication:** Create `users` and `data_entries` tables. Store user credentials securely using `passlib` with `bcrypt`. Provide JWT-based authentication endpoints under `/api/auth`.
2. **Data Management:** Implement data validation and manual entry. Create endpoints `/api/data/upload`, `/api/data/validate`, and `/api/data/import`. Ensure observations clearly map the source type (`ORIGINAL_DATASET`, `UPLOADED_DATASET`, `MANUAL_ENTRY`, `SIMULATED`) for academic provenance.
3. **Role-Based Views:** Control React navbar tabs based on the logged-in user's role (ADMIN, PLANNER, VIEWER). Create Login and Data Management pages, keeping the existing dashboard components completely intact.
