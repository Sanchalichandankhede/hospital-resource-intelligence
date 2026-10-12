from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from backend.database import get_db
from backend.models.db_models import Alert
from backend.schemas.models import AlertListResponse, AlertResponse
from backend.routers.forecast import validate_dates

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=AlertListResponse)
def get_alerts(
    resource: Optional[str] = Query(None, description="Resource type (e.g., 'ICU Beds', 'ED Arrivals')"),
    risk_level: Optional[str] = Query(None, description="Risk level ('LOW', 'MEDIUM', 'HIGH')"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    parsed_start, parsed_end = validate_dates(start_date, end_date)
    
    query = db.query(Alert)
    
    if resource:
        query = query.filter(Alert.resource == resource)
    if risk_level:
        risk_level_upper = risk_level.upper()
        if risk_level_upper not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise HTTPException(status_code=400, detail="Invalid risk_level. Use 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'.")
        query = query.filter(Alert.risk_level == risk_level_upper)
    if parsed_start:
        query = query.filter(Alert.alert_date >= parsed_start)
    if parsed_end:
        query = query.filter(Alert.alert_date <= parsed_end)
        
    results = query.order_by(Alert.alert_date.asc(), Alert.resource.asc()).all()
    
    return AlertListResponse(
        alerts=[AlertResponse.model_validate(r) for r in results]
    )
