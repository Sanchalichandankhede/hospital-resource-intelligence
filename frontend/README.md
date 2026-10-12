# Hospital Resource Intelligence Frontend Dashboard

This folder contains the React frontend dashboard built using Vite, Recharts, and Lucide Icons, connected to the FastAPI backend.

---

## 1. Setup and Installation

### Dependencies
Install the required node modules:
```bash
npm install
```

### Environment Variables
Configure the API endpoint address. Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Inside `.env`, verify the base API address:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 2. Starting the Development Server

Start the local React development client:
```bash
npm run dev
```
The server will start at `http://localhost:5173`. Open this URL in your browser to view the dashboard.

---

## 3. Backend Dependency
Ensure that the FastAPI backend server is running concurrently on port `8000` so the client can query metrics:
```bash
# In the project root directory:
uvicorn backend.main:app --reload
```

---

## 4. Dashboard Sections
The application implements sidebar navigation to switch between the following sections:
1. **Overview:** Summary dashboard displaying peak ICU occupancy, peak ED daily arrivals, risk statuses, and forecast horizons alongside interactive forecast charts and alerts tables.
2. **Forecasts:** Interactive 7-day line charts comparing historical actuals vs predicted demands for both ICU Beds and ED Arrivals. Supports model selections.
3. **Risk Alerts:** List of computed shortage threats with risk levels (Low, Medium, High), capacity gaps, and reasons. Supports filters.
4. **Recommendations:** Relational action panel mapping risk levels to administrative suggestions.
5. **Explainable AI:** Feature contribution charts using SHAP and LIME relative bar weights.
6. **Model Performance:** Model metrics benchmarking table automatically highlighting the model with the lowest MAE score.
