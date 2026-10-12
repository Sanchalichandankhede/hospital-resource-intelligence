from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional
import pandas as pd
import io
import math
from pydantic import BaseModel

from backend.database import get_db
from backend.models.db_models import DataEntry, User, Dataset
from backend.routers.auth import get_current_user, require_role
from ml.pipeline.forecast_pipeline import generate_dynamic_forecast

router = APIRouter(prefix="/api/data", tags=["data"])

# Pydantic models
class DataEntryItem(BaseModel):
    date: str
    resource: str
    value: float

class ImportRequest(BaseModel):
    filename: str = "imported_dataset.csv"
    entries: List[DataEntryItem]

class ManualEntryRequest(BaseModel):
    date: str
    icu_demand: Optional[float] = None
    general_bed_demand: Optional[float] = None
    emergency_bed_demand: Optional[float] = None
    oxygen_demand: Optional[float] = None
    blood_demand: Optional[float] = None
    staff_requirement: Optional[float] = None
    ambulance_requirement: Optional[float] = None

class DataEntryResponse(BaseModel):
    id: int
    date: date
    resource: str
    value: float
    source_type: str
    created_by_username: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class DatasetResponse(BaseModel):
    id: int
    filename: Optional[str]
    source_type: str
    uploaded_by_username: Optional[str]
    uploaded_at: str
    created_at: Optional[str] = None
    resource_type: Optional[str] = None
    resource_category: Optional[str] = None
    row_count: int
    validation_status: str
    processing_status: str
    forecast_status: Optional[str]

    class Config:
        from_attributes = True

class ForecastGenerateRequest(BaseModel):
    dataset_id: int
    model: str
    retrain: bool = False

VALID_RESOURCES = [
    "ICU Demand",
    "General Bed Demand",
    "Emergency Bed Demand",
    "Oxygen Demand",
    "Blood Demand",
    "Staff Requirement",
    "Ambulance Requirement"
]

@router.post("/upload")
def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    # Check file extension
    filename = file.filename
    if not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only CSV (.csv) and Excel (.xlsx) are supported."
        )

    try:
        contents = file.file.read()
        # Limit file size to 5MB
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds the 5MB limit.")

        # Read CSV or Excel
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Validation Checks
    errors = []
    warnings = []
    detected_columns = list(df.columns)
    
    # Required columns check
    required_cols = ["date", "resource", "value"]
    missing_cols = [c for c in required_cols if c not in detected_columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return {
            "valid": False,
            "filename": filename,
            "rows": len(df),
            "columns_detected": detected_columns,
            "errors": errors,
            "warnings": warnings,
            "preview": []
        }

    preview_rows = []
    seen_combinations = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed plus header row
        
        # 1. Parse date
        d_val = row.get("date")
        parsed_date = None
        if pd.isna(d_val):
            errors.append(f"Row {row_num}: Date is missing.")
        else:
            try:
                parsed_date = pd.to_datetime(d_val).date()
            except Exception:
                errors.append(f"Row {row_num}: Invalid date format '{d_val}'.")

        # 2. Parse resource name
        r_val = row.get("resource")
        if pd.isna(r_val):
            errors.append(f"Row {row_num}: Resource is missing.")
        else:
            r_clean = str(r_val).strip()
            if r_clean not in VALID_RESOURCES:
                errors.append(f"Row {row_num}: Unknown resource name '{r_clean}'.")

        # 3. Parse value
        v_val = row.get("value")
        parsed_value = None
        if pd.isna(v_val):
            errors.append(f"Row {row_num}: Value is missing.")
        else:
            try:
                parsed_value = float(v_val)
                if parsed_value < 0:
                    errors.append(f"Row {row_num}: Negative resource quantity '{parsed_value}' is invalid.")
            except ValueError:
                errors.append(f"Row {row_num}: Value '{v_val}' must be numeric.")

        # 4. Duplicate checks
        if parsed_date and r_val:
            combo = (str(parsed_date), str(r_val).strip())
            if combo in seen_combinations:
                warnings.append(f"Row {row_num}: Duplicate entry for date '{parsed_date}' and resource '{r_val}'.")
            seen_combinations.add(combo)

        # Assemble preview row if parsed successfully
        if parsed_date and r_val and parsed_value is not None:
            preview_rows.append({
                "date": str(parsed_date),
                "resource": str(r_val).strip(),
                "value": parsed_value
            })

    # Return summary validation response
    is_valid = len(errors) == 0
    return {
        "valid": is_valid,
        "filename": filename,
        "rows": len(df),
        "columns_detected": detected_columns,
        "errors": errors,
        "warnings": warnings,
        "preview": preview_rows
    }

@router.post("/import")
def import_dataset(
    req: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    # 1. Create a Dataset tracking batch record
    db_dataset = Dataset(
        filename=req.filename,
        source_type="CSV_UPLOAD" if req.filename.endswith(".csv") else "EXCEL_UPLOAD",
        uploaded_by=current_user.id,
        row_count=len(req.entries),
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)

    imported_count = 0
    for item in req.entries:
        try:
            parsed_date = date.fromisoformat(item.date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {item.date}")

        if item.resource not in VALID_RESOURCES:
            raise HTTPException(status_code=400, detail=f"Invalid resource target: {item.resource}")

        if item.value < 0:
            raise HTTPException(status_code=400, detail="Resource value cannot be negative.")

        # Upsert: check if duplicate combination of date, resource, source exists
        existing = db.query(DataEntry).filter_by(
            date=parsed_date,
            resource=item.resource,
            source_type="UPLOADED_DATASET"
        ).first()

        if existing:
            existing.value = item.value
            existing.created_by = current_user.id
            existing.dataset_id = db_dataset.id
        else:
            db_entry = DataEntry(
                date=parsed_date,
                resource=item.resource,
                value=item.value,
                source_type="UPLOADED_DATASET",
                created_by=current_user.id,
                dataset_id=db_dataset.id
            )
            db.add(db_entry)
        imported_count += 1

    db.commit()
    return {
        "status": "success",
        "dataset_id": db_dataset.id,
        "detail": f"Successfully imported {imported_count} dataset records.",
        "retraining_triggered": False,
        "retraining_notice": "Data imported successfully. Model retraining is not automatically performed."
    }

@router.post("/manual")
def create_manual_entry(
    req: ManualEntryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    try:
        parsed_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    mapped_fields = {
        "ICU Demand": req.icu_demand,
        "General Bed Demand": req.general_bed_demand,
        "Emergency Bed Demand": req.emergency_bed_demand,
        "Oxygen Demand": req.oxygen_demand,
        "Blood Demand": req.blood_demand,
        "Staff Requirement": req.staff_requirement,
        "Ambulance Requirement": req.ambulance_requirement
    }

    # First check we have at least one value
    has_values = any(v is not None for v in mapped_fields.values())
    if not has_values:
        raise HTTPException(status_code=400, detail="At least one resource value must be entered.")

    # Determine resource type if single resource or multi
    present_resources = [k for k, v in mapped_fields.items() if v is not None]
    res_label = present_resources[0] if len(present_resources) == 1 else "Multi-Resource"

    # Create manual tracking batch
    db_dataset = Dataset(
        filename="Manual Entry",
        source_type="MANUAL_ENTRY",
        uploaded_by=current_user.id,
        resource_type=res_label,
        row_count=0,
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)

    inserted_count = 0
    for resource_name, val in mapped_fields.items():
        if val is None:
            continue
            
        if val < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Value for '{resource_name}' cannot be negative."
            )

        # Upsert for manual entry
        existing = db.query(DataEntry).filter_by(
            date=parsed_date,
            resource=resource_name,
            source_type="MANUAL_ENTRY"
        ).first()

        if existing:
            existing.value = val
            existing.created_by = current_user.id
            existing.dataset_id = db_dataset.id
        else:
            db_entry = DataEntry(
                date=parsed_date,
                resource=resource_name,
                value=val,
                source_type="MANUAL_ENTRY",
                created_by=current_user.id,
                dataset_id=db_dataset.id
            )
            db.add(db_entry)
        inserted_count += 1

    # Update row count
    db_dataset.row_count = inserted_count
    db.commit()
    
    return {
        "status": "success",
        "dataset_id": db_dataset.id,
        "detail": f"Successfully recorded {inserted_count} manual observations.",
        "retraining_triggered": False,
        "retraining_notice": "Data recorded successfully. Model retraining is not automatically performed."
    }

@router.get("/entries", response_model=List[DataEntryResponse])
def get_data_entries(db: Session = Depends(get_db)):
    results = db.query(DataEntry).order_by(DataEntry.date.desc(), DataEntry.resource.asc()).all()
    
    response_list = []
    for r in results:
        username = r.user.username if r.user else None
        response_list.append({
            "id": r.id,
            "date": r.date,
            "resource": r.resource,
            "value": float(r.value),
            "source_type": r.source_type,
            "created_by_username": username,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return response_list

@router.get("/datasets", response_model=List[DatasetResponse])
def get_datasets(db: Session = Depends(get_db)):
    results = db.query(Dataset).order_by(Dataset.uploaded_at.desc(), Dataset.id.desc()).all()
    
    response_list = []
    for r in results:
        username = r.user.username if r.user else "Admin"
        display_filename = r.filename if (r.filename and r.source_type != "MANUAL_ENTRY") else "Manual Entry"
        display_resource = r.resource_type or ("Multi-Resource" if r.source_type != "MANUAL_ENTRY" else "ICU Beds")
        display_status = "SAVED" if r.source_type == "MANUAL_ENTRY" else ("IMPORTED" if r.processing_status in ["STORED", "PROCESSED"] else r.processing_status)
        timestamp_str = r.uploaded_at.isoformat() if r.uploaded_at else ""

        response_list.append({
            "id": r.id,
            "filename": display_filename,
            "source_type": r.source_type,
            "uploaded_by_username": username,
            "uploaded_at": timestamp_str,
            "created_at": timestamp_str,
            "resource_type": display_resource,
            "resource_category": display_resource,
            "row_count": r.row_count,
            "validation_status": r.validation_status,
            "processing_status": display_status,
            "forecast_status": r.forecast_status
        })
    return response_list

@router.post("/forecast/generate")
def generate_forecast(
    req: ForecastGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    try:
        res = generate_dynamic_forecast(db, req.model, req.dataset_id, req.retrain)
        if not res["success"]:
            raise HTTPException(status_code=400, detail=res["detail"])
        return res
    except HTTPException as http_err:
        raise http_err
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal forecast execution failure: {str(e)}")
