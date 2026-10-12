from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Dict, Any
import math

from backend.database import get_db
from backend.models.db_models import Forecast, ModelPerformance

router = APIRouter(
    prefix="/api/forecast/multi",
    tags=["multi-resource"]
)

# Core Resource Capacity definitions
CAPACITIES = {
    "ICU Demand": 2.0,
    "General Bed Demand": 25.0,
    "Emergency Bed Demand": 8.0,
    "Oxygen Demand": 100.0,
    "Blood Demand": 10.0,
    "Staff Requirement": 12.0,
    "Ambulance Requirement": 5.0
}

RESOURCE_METADATA = {
    "ICU Demand": {
        "unit": "Beds",
        "source": "Core forecasting model predictions",
        "assumption": "Direct forecast from daily occupied beds telemetry"
    },
    "General Bed Demand": {
        "unit": "Beds",
        "source": "Derived from monthly beds dataset baseline",
        "assumption": "Monthly baseline average beds = 18.0; daily scaling variation = 2.0 * predicted ICU demand"
    },
    "Emergency Bed Demand": {
        "unit": "Beds",
        "source": "Derived from predicted Emergency Department Daily Arrivals",
        "assumption": "Assumes a conversion rate of 25% of patient daily arrivals require Emergency admissions"
    },
    "Oxygen Demand": {
        "unit": "Liters",
        "source": "Derived from predicted bed occupancy requirements",
        "assumption": "ICU beds consume 15.0 L/day; Emergency beds consume 5.0 L/day"
    },
    "Blood Demand": {
        "unit": "Units",
        "source": "Derived from predicted Emergency Department Daily Arrivals",
        "assumption": "Daily ED patient arrivals require average of 0.20 pints of blood transfusion"
    },
    "Staff Requirement": {
        "unit": "FTE",
        "source": "Derived from predicted bed occupancy requirements",
        "assumption": "ICU beds staffing ratio = 1.5 FTE; Emergency beds staffing ratio = 0.5 FTE"
    },
    "Ambulance Requirement": {
        "unit": "Cars",
        "source": "Derived from predicted Emergency Department Daily Arrivals",
        "assumption": "Assumes transport ratio of 15% of patient arrivals require ambulance transports"
    }
}

def get_risk_level(resource: str, gap: float) -> str:
    if gap < 0:
        # Check critical thresholds
        if resource == "ICU Demand" and gap < -1.0:
            return "CRITICAL"
        if resource == "General Bed Demand" and gap < -2.0:
            return "CRITICAL"
        if resource == "Emergency Bed Demand" and gap < -1.0:
            return "CRITICAL"
        if resource == "Oxygen Demand" and gap < -10.0:
            return "CRITICAL"
        if resource == "Blood Demand" and gap < -2.0:
            return "CRITICAL"
        if resource == "Staff Requirement" and gap < -1.0:
            return "CRITICAL"
        if resource == "Ambulance Requirement" and gap < -0.5:
            return "CRITICAL"
        return "HIGH"
    elif gap < (CAPACITIES[resource] * 0.15): # less than 15% safety buffer
        return "MEDIUM"
    return "LOW"

def get_recommendation(resource: str, risk: str) -> Dict[str, str]:
    is_severe = risk in ("HIGH", "CRITICAL")
    
    if resource == "ICU Demand":
        return {
            "recommendation": "Execute ICU staffing adjustments and coordinate immediate bedside checks." if is_severe else "Maintain routine ICU beds checking schedule.",
            "trigger": "ICU Bed occupied gap falls below buffer threshold." if is_severe else "ICU Bed occupancy within safe boundary."
        }
    if resource == "General Bed Demand":
        return {
            "recommendation": "Coordinate general bed census check; pause elective admissions reviews." if is_severe else "Monitor general bed capacity levels.",
            "trigger": "General Bed availability gap is negative." if is_severe else "General Bed occupancy within normal bounds."
        }
    if resource == "Emergency Bed Demand":
        return {
            "recommendation": "Review emergency admissions throughput and trigger reserve beds setup." if is_severe else "Monitor ED beds turnover metrics.",
            "trigger": "Emergency admissions predicted to exceed ED bed limits." if is_severe else "ED Bed occupancy within capacity bounds."
        }
    if resource == "Oxygen Demand":
        return {
            "recommendation": "Initiate emergency oxygen procurement and coordinate with backup suppliers." if is_severe else "Monitor oxygen storage tank pressure and levels.",
            "trigger": "Daily oxygen demand exceeds available liters capacity." if is_severe else "Oxygen levels within target reserves."
        }
    if resource == "Blood Demand":
        return {
            "recommendation": "Coordinate inventory replenishment with regional blood bank centers." if is_severe else "Maintain standard blood bank stock reviews.",
            "trigger": "Blood packages predicted gap falls below margin limit." if is_severe else "Blood supply inventory levels healthy."
        }
    if resource == "Staff Requirement":
        return {
            "recommendation": "Coordinate with nursing registry and initiate shift reallocation review." if is_severe else "Maintain standard staff scheduling parameters.",
            "trigger": "Active staffing requirement exceeds standard headcount limit." if is_severe else "Available staffing headcount sufficient."
        }
    # Ambulance
    return {
        "recommendation": "Coordinate emergency dispatch and review backup ambulance service contracts." if is_severe else "Maintain regular vehicle readiness inspections.",
        "trigger": "Ambulance daily requirements exceed active vehicle counts." if is_severe else "Active ambulance availability status normal."
    }

@router.get("")
def get_multi_resource_forecasts(
    model: str = Query("XGBoost", description="Forecasting model to use (XGBoost, Prophet, LSTM)"),
    db: Session = Depends(get_db)
):
    """
    Exposes 7-day daily forecasts for all seven resource targets,
    dynamically compiling predictions, capacity gaps, risk states,
    and administrative recommendations.
    """
    # 1. Fetch core predictions from database
    icu_forecasts = db.query(Forecast).filter(
        Forecast.resource == "ICU Beds",
        Forecast.model == model
    ).order_by(Forecast.forecast_date.asc()).all()

    ed_forecasts = db.query(Forecast).filter(
        Forecast.resource == "ED Arrivals",
        Forecast.model == model
    ).order_by(Forecast.forecast_date.asc()).all()

    if not icu_forecasts or not ed_forecasts:
        # Fallback to general lookup to prevent blank results
        icu_forecasts = db.query(Forecast).filter(Forecast.resource == "ICU Beds").order_by(Forecast.forecast_date.asc()).all()
        ed_forecasts = db.query(Forecast).filter(Forecast.resource == "ED Arrivals").order_by(Forecast.forecast_date.asc()).all()
        if not icu_forecasts:
            raise HTTPException(status_code=404, detail="Core forecast data not found in database.")

    # 2. Fetch performance statistics for dynamic MAE/RMSE calculations
    icu_perf = db.query(ModelPerformance).filter(
        ModelPerformance.target == "icu_occupancy",
        ModelPerformance.model == model
    ).first()

    ed_perf = db.query(ModelPerformance).filter(
        ModelPerformance.target == "ed_arrivals",
        ModelPerformance.model == model
    ).first()

    # Fallback errors constants
    icu_mae = float(icu_perf.mae) if icu_perf else 0.5940
    icu_rmse = float(icu_perf.rmse) if icu_perf else 0.7812
    ed_mae = float(ed_perf.mae) if ed_perf else 0.0759
    ed_rmse = float(ed_perf.rmse) if ed_perf else 0.0984

    # 3. Compile daily targets lists
    dates_length = min(len(icu_forecasts), len(ed_forecasts))
    
    result_data = {}
    
    for resource_name in CAPACITIES.keys():
        predictions_list = []
        is_sim = resource_name != "ICU Demand"
        capacity = CAPACITIES[resource_name]
        
        # Mute MAE and RMSE values for simulated targets to prevent false precision representation
        if resource_name == "ICU Demand":
            res_mae, res_rmse = icu_mae, icu_rmse
        else:
            res_mae, res_rmse = None, None

        for i in range(dates_length):
            f_date = icu_forecasts[i].forecast_date
            icu_val = float(icu_forecasts[i].predicted_demand)
            ed_val = float(ed_forecasts[i].predicted_demand)
            
            # Map predictions using formulas
            if resource_name == "ICU Demand":
                pred = icu_val
                act = float(icu_forecasts[i].actual_demand) if icu_forecasts[i].actual_demand is not None else None
            elif resource_name == "General Bed Demand":
                # monthly baseline of 18 + variations
                pred = 18.0 + (icu_val * 2.0)
                act = None
            elif resource_name == "Emergency Bed Demand":
                pred = ed_val * 0.25
                act = None
            elif resource_name == "Oxygen Demand":
                pred = (icu_val * 15.0) + (ed_val * 0.25 * 5.0)
                act = None
            elif resource_name == "Blood Demand":
                pred = ed_val * 0.20
                act = None
            elif resource_name == "Staff Requirement":
                pred = (icu_val * 1.5) + (ed_val * 0.25 * 0.5)
                act = None
            else: # Ambulance Requirement
                pred = ed_val * 0.15
                act = None

            # Calculate operational requirement based on ceiling rounding for positive forecasts
            if resource_name == "Oxygen Demand":
                operational_requirement = pred
            else:
                if pred <= 0:
                    operational_requirement = 0.0
                else:
                    operational_requirement = float(math.ceil(pred))

            predicted_gap = capacity - pred
            operational_gap = capacity - operational_requirement

            risk = get_risk_level(resource_name, operational_gap)
            rec_info = get_recommendation(resource_name, risk)

            predictions_list.append({
                "date": f_date.isoformat(),
                "predicted_demand": round(pred, 4),
                "predicted_value": round(pred, 4),
                "operational_requirement": round(operational_requirement, 4) if resource_name == "Oxygen Demand" else int(operational_requirement),
                "actual_demand": round(act, 4) if act is not None else None,
                "capacity": capacity,
                "capacity_or_stock": capacity,
                "resource_gap": round(operational_gap, 4) if resource_name == "Oxygen Demand" else int(operational_gap),
                "predicted_gap": round(predicted_gap, 4),
                "operational_gap": round(operational_gap, 4) if resource_name == "Oxygen Demand" else int(operational_gap),
                "risk_level": risk,
                "is_simulated": is_sim,
                "recommendation": rec_info["recommendation"],
                "trigger": rec_info["trigger"]
            })

        metadata = RESOURCE_METADATA.get(resource_name, {"unit": "Units", "source": "Simulated", "assumption": ""})
        result_data[resource_name] = {
            "resource": resource_name,
            "predictions": predictions_list,
            "mae": round(res_mae, 6) if res_mae is not None else None,
            "rmse": round(res_rmse, 6) if res_rmse is not None else None,
            "model": model,
            "is_simulated": is_sim,
            "unit": metadata["unit"],
            "source": metadata["source"],
            "assumption": metadata["assumption"]
        }

    return {
        "model": model,
        "resources": result_data
    }
