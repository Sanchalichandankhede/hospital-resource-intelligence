from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
import uvicorn

from backend.config import CORS_ORIGINS
from backend.database import get_db
from backend.routers import forecast, alerts, recommendations, explanations, performance, multi_resource, auth, data, resources

app = FastAPI(
    title="Hospital Resource Intelligence API",
    description="Operational resource demand forecasting and alert decision engine backend.",
    version="1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom safety header middleware
@app.middleware("http")
async def add_clinical_disclaimer_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Clinical-Notice"] = (
        "Operational metrics only. Systems must not be used for diagnosis or patient treatment decisions"
    )
    return response

# Include all modular routers
app.include_router(auth.router)
app.include_router(data.router)
app.include_router(forecast.router)
app.include_router(alerts.router)
app.include_router(recommendations.router)
app.include_router(explanations.router)
app.include_router(performance.router)
app.include_router(multi_resource.router)
app.include_router(resources.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Diagnostics endpoint to verify server and database connectivity.
    """
    db_status = "healthy"
    try:
        # Perform simple low-overhead SQL validation query
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return {
        "status": "healthy",
        "database": db_status
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
