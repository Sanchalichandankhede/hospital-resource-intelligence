# Stage 17 — Data-to-Forecast Audit Report

## 1. Current Data Flow
* Files are uploaded via `POST /api/data/upload` in [`backend/routers/data.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/routers/data.py), validated in-memory, and returned to the client as a preview.
* If approved, the client POSTs the rows to `POST /api/data/import`, which writes them to the `data_entries` table in the database with a source type of `UPLOADED_DATASET`.
* Manual entry POSTs to `POST /api/data/manual`, which writes them to the `data_entries` table as `MANUAL_ENTRY`.
* Historical daily telemetry starts as processed CSV files loaded during database seeding into `historical_demand`.

## 2. Current Forecast Flow
* Models are trained in batch scripts (`train.py` inside `ml/forecasting/xgboost`, `prophet`, and `lstm`), reading from the processed files `icu_daily_processed.csv` and `ed_daily_processed.csv`.
* The scripts output forecasts to `data/interim/*.csv`.
* During seeding, these interim forecast CSVs are loaded into the `forecasts` database table.
* The frontend reads forecasts through the FastAPI backend routers.

## 3. Missing Connections
* Newly uploaded/manually entered records stored in the `data_entries` table are never read by the preprocessing or model training pipelines.
* The model pipelines only read from static files (`data/processed/*.csv`), and do not have an automated trigger to run on demand.
* The system lacks a batch/dataset tracking mechanism to trace which specific historical dataset version generated which specific forecast.

## 4. Proposed Architecture
1. **Schema Enhancements:**
   - Create a new `datasets` table tracking batch metadata, validation, and processing/forecast generation statuses.
   - Link `data_entries` and `forecasts` to `datasets(id)` using foreign keys.
2. **Pre-processing and Pipeline Connector:**
   - Create a clean pipeline connector `ml/pipeline/forecast_pipeline.py`.
   - On request, this pipeline will compile the complete historical baseline by merging `historical_demand` (original telemetry) with active, user-imported datasets or manual entries for the target resources.
   - Run daily feature generator to update features.
   - Run model prediction (Prophet, XGBoost, LSTM) on the updated sequence to forecast the next 7 days.
   - Store predictions directly to the database with a link to the active `dataset_id`.
3. **Control Actions:**
   - Expose endpoints:
     - `POST /api/data/forecast/generate` (triggers the forecast generation workflow)
     - `POST /api/data/forecast/retrain` (triggers retraining on updated historical data if requested)

## 5. Files to be Modified
* [`database/schema.sql`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/database/schema.sql)
* [`backend/models/db_models.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/models/db_models.py)
* [`database/load_data.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/database/load_data.py)
* [`backend/routers/data.py`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/backend/routers/data.py)
* [`frontend/src/pages/DataManagement.jsx`](file:///Users/sanchalichandankhede/Documents/Idea%20lab/hospital-resource-intelligence/frontend/src/pages/DataManagement.jsx)
