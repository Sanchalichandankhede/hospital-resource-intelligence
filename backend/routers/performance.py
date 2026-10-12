from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import ModelPerformance
from backend.schemas.models import ModelPerformanceListResponse, ModelPerformanceResponse

router = APIRouter(prefix="/api/model-performance", tags=["performance"])

@router.get("", response_model=ModelPerformanceListResponse)
def get_model_performance(db: Session = Depends(get_db)):
    results = db.query(ModelPerformance).order_by(
        ModelPerformance.target.asc(),
        ModelPerformance.rank.asc()
    ).all()
    
    return ModelPerformanceListResponse(
        metrics=[ModelPerformanceResponse.model_validate(r) for r in results]
    )
