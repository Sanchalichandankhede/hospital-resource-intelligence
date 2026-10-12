from pydantic import BaseModel, Field
import datetime as dt
from typing import List, Optional

# Base Configuration for SQLAlchemy serialization compatibility in Pydantic v2
class ORMBase(BaseModel):
    model_config = {"from_attributes": True}  # Pydantic v2


# 1. Forecast Schemas
class ForecastItem(ORMBase):
    date: dt.date = Field(..., serialization_alias="date", validation_alias="forecast_date")
    predicted_demand: float
    actual_demand: Optional[float] = None
    created_timestamp: dt.datetime


class ForecastListResponse(BaseModel):
    resource: str
    model: str
    forecast_horizon: str
    predictions: List[ForecastItem]


# 2. Alert Schemas
class AlertResponse(ORMBase):
    id: int
    alert_date: dt.date = Field(..., serialization_alias="date", validation_alias="alert_date")
    resource: str
    predicted_demand: float
    actual_capacity: Optional[float] = None
    simulated_capacity: float
    is_capacity_simulated: bool
    capacity_gap: float
    risk_level: str
    reason: str


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]


# 3. Recommendation Schemas
class RecommendationResponse(ORMBase):
    id: int
    alert_id: Optional[int] = None
    date: dt.date
    resource: str
    risk_level: str
    recommendation: str
    trigger: str
    model: str


class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationResponse]


# 4. Explanation Schemas
class ExplanationItem(ORMBase):
    feature: str
    feature_value: float
    contribution: float
    direction: int


class ExplanationListResponse(BaseModel):
    resource: str
    date: dt.date
    model: str
    explanation_method: str
    explanations: List[ExplanationItem]


# 5. Model Performance Schemas
class ModelPerformanceResponse(ORMBase):
    model: str
    target: str
    mae: float
    rmse: float
    mape: Optional[float] = None
    evaluation_period: str
    rank: int


class ModelPerformanceListResponse(BaseModel):
    metrics: List[ModelPerformanceResponse]
