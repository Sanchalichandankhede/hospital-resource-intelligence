from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.db_models import Recommendation
from backend.schemas.models import RecommendationListResponse, RecommendationResponse

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.get("", response_model=RecommendationListResponse)
def get_recommendations(
    resource: Optional[str] = Query(None, description="Resource type (e.g., 'ICU Beds', 'ED Arrivals')"),
    risk_level: Optional[str] = Query(None, description="Risk level ('LOW', 'MEDIUM', 'HIGH')"),
    db: Session = Depends(get_db)
):
    query = db.query(Recommendation)
    
    if resource:
        query = query.filter(Recommendation.resource == resource)
    if risk_level:
        query = query.filter(Recommendation.risk_level == risk_level.upper())
        
    results = query.order_by(Recommendation.date.asc(), Recommendation.resource.asc()).all()
    
    return RecommendationListResponse(
        recommendations=[RecommendationResponse.model_validate(r) for r in results]
    )
