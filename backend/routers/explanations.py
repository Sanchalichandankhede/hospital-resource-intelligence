from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional

from backend.database import get_db
from backend.models.db_models import Explanation
from backend.schemas.models import ExplanationListResponse, ExplanationItem

router = APIRouter(prefix="/api/explanations", tags=["explanations"])

def validate_explanation_method(method: Optional[str]):
    if method:
        method_upper = method.upper()
        if method_upper not in ["SHAP", "LIME"]:
            raise HTTPException(status_code=400, detail="Invalid explanation_method. Use 'SHAP' or 'LIME'.")
        return method_upper
    return "SHAP"

def validate_iso_date(date_str: Optional[str]):
    if date_str:
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    return None

@router.get("/icu", response_model=ExplanationListResponse)
def get_icu_explanations(
    date: Optional[str] = Query(None, description="Explanation target forecast date (YYYY-MM-DD)"),
    method: Optional[str] = Query(None, description="Explanation method ('SHAP' or 'LIME')"),
    db: Session = Depends(get_db)
):
    parsed_date = validate_iso_date(date)
    parsed_method = validate_explanation_method(method)
    resource_name = "ICU Beds"
    
    query = db.query(Explanation).filter(
        Explanation.resource == resource_name,
        Explanation.explanation_method == parsed_method
    )
    
    if parsed_date:
        query = query.filter(Explanation.date == parsed_date)
        
    results = query.order_by(Explanation.contribution.desc()).all()
    
    # Use the first record's date if date is not specified, otherwise use parsed_date or default
    result_date = parsed_date if parsed_date else (results[0].date if results else date.fromisoformat("2137-10-17"))
    
    return ExplanationListResponse(
        resource=resource_name,
        date=result_date,
        model="XGBoost",
        explanation_method=parsed_method,
        explanations=[ExplanationItem.model_validate(r) for r in results]
    )

@router.get("/ed", response_model=ExplanationListResponse)
def get_ed_explanations(
    date: Optional[str] = Query(None, description="Explanation target forecast date (YYYY-MM-DD)"),
    method: Optional[str] = Query(None, description="Explanation method ('SHAP' or 'LIME')"),
    db: Session = Depends(get_db)
):
    parsed_date = validate_iso_date(date)
    parsed_method = validate_explanation_method(method)
    resource_name = "ED Arrivals"
    
    query = db.query(Explanation).filter(
        Explanation.resource == resource_name,
        Explanation.explanation_method == parsed_method
    )
    
    if parsed_date:
        query = query.filter(Explanation.date == parsed_date)
        
    results = query.order_by(Explanation.contribution.desc()).all()
    
    result_date = parsed_date if parsed_date else (results[0].date if results else date.fromisoformat("2148-01-25"))
    
    return ExplanationListResponse(
        resource=resource_name,
        date=result_date,
        model="XGBoost",
        explanation_method=parsed_method,
        explanations=[ExplanationItem.model_validate(r) for r in results]
    )
