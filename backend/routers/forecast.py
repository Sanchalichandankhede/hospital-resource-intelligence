from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, List

from backend.database import get_db
from backend.models.db_models import Forecast
from backend.schemas.models import ForecastListResponse, ForecastItem

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

def validate_dates(start_date: Optional[str], end_date: Optional[str]):
    """
    Parses and validates ISO date parameters.
    """
    parsed_start = None
    parsed_end = None
    
    if start_date:
        try:
            parsed_start = date.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD.")
            
    if end_date:
        try:
            parsed_end = date.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD.")
            
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date.")
        
    return parsed_start, parsed_end

@router.get("/icu", response_model=ForecastListResponse)
def get_icu_forecast(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    model: str = Query("XGBoost", description="Model name (e.g., XGBoost, Prophet, LSTM)"),
    db: Session = Depends(get_db)
):
    parsed_start, parsed_end = validate_dates(start_date, end_date)
    resource_name = "ICU Beds"
    
    query = db.query(Forecast).filter(
        Forecast.resource == resource_name,
        Forecast.model == model
    )
    
    if parsed_start:
        query = query.filter(Forecast.forecast_date >= parsed_start)
    if parsed_end:
        query = query.filter(Forecast.forecast_date <= parsed_end)
        
    results = query.order_by(Forecast.forecast_date.asc()).all()
    
    return ForecastListResponse(
        resource=resource_name,
        model=model,
        forecast_horizon="7 days",
        predictions=[ForecastItem.model_validate(r) for r in results]
    )

@router.get("/ed", response_model=ForecastListResponse)
def get_ed_forecast(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    model: str = Query("XGBoost", description="Model name (e.g., XGBoost, Prophet, LSTM)"),
    db: Session = Depends(get_db)
):
    parsed_start, parsed_end = validate_dates(start_date, end_date)
    resource_name = "ED Arrivals"
    
    query = db.query(Forecast).filter(
        Forecast.resource == resource_name,
        Forecast.model == model
    )
    
    if parsed_start:
        query = query.filter(Forecast.forecast_date >= parsed_start)
    if parsed_end:
        query = query.filter(Forecast.forecast_date <= parsed_end)
        
    results = query.order_by(Forecast.forecast_date.asc()).all()
    
    return ForecastListResponse(
        resource=resource_name,
        model=model,
        forecast_horizon="7 days",
        predictions=[ForecastItem.model_validate(r) for r in results]
    )
