from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.db_models import (
    BedRecord, OxygenRecord, BloodRecord, StaffRecord, AmbulanceRecord,
    User, DataEntry, Dataset
)
from backend.routers.auth import require_role

router = APIRouter(prefix="/api/resources", tags=["resources"])

# --- Pydantic Schema Declarations ---

# Bed Record Schemas
class BedRecordCreate(BaseModel):
    date: str
    bed_type: str = Field(..., description="ICU Beds, General Beds, or Emergency Beds")
    available_count: int = Field(..., ge=0)
    occupied_count: int = Field(..., ge=0)
    required_count: int = Field(..., ge=0)

class BedRecordResponse(BaseModel):
    id: int
    date: date
    bed_type: str
    available_count: int
    occupied_count: int
    required_count: int
    source_type: str
    created_by_username: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

# Oxygen Record Schemas
class OxygenRecordCreate(BaseModel):
    date: str
    total_cylinders: int = Field(..., ge=0)
    available_cylinders: int = Field(..., ge=0)
    used_cylinders: int = Field(..., ge=0)
    filled_refilled: int = Field(..., ge=0)
    required_cylinders: int = Field(..., ge=0)
    notes: Optional[str] = None

class OxygenRecordResponse(BaseModel):
    id: int
    date: date
    total_cylinders: int
    available_cylinders: int
    used_cylinders: int
    filled_refilled: int
    required_cylinders: int
    source_type: str
    created_by_username: Optional[str]
    created_at: str
    notes: Optional[str]

    class Config:
        from_attributes = True

# Blood Record Schemas
class BloodRecordCreate(BaseModel):
    date: str
    blood_group: str = Field(..., description="A+, A-, B+, B-, AB+, AB-, O+, O-")
    available_units: int = Field(..., ge=0)
    used_units: int = Field(..., ge=0)
    received_units: int = Field(..., ge=0)
    reserved_units: int = Field(..., ge=0)
    required_units: int = Field(..., ge=0)

class BloodRecordResponse(BaseModel):
    id: int
    date: date
    blood_group: str
    available_units: int
    used_units: int
    received_units: int
    reserved_units: int
    required_units: int
    source_type: str
    created_by_username: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

# Staff Record Schemas
class StaffRecordCreate(BaseModel):
    date: str
    staff_category: str = Field(..., description="Doctors, Nurses, Technicians, Support Staff")
    available_count: int = Field(..., ge=0)
    assigned_count: int = Field(..., ge=0)
    used_count: int = Field(..., ge=0)
    required_count: int = Field(..., ge=0)
    shift: Optional[str] = None
    notes: Optional[str] = None

class StaffRecordResponse(BaseModel):
    id: int
    date: date
    staff_category: str
    available_count: int
    assigned_count: int
    used_count: int
    required_count: int
    source_type: str
    created_by_username: Optional[str]
    created_at: str
    shift: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True

# Ambulance Record Schemas
class AmbulanceRecordCreate(BaseModel):
    date: str
    total_ambulances: int = Field(..., ge=0)
    available_count: int = Field(..., ge=0)
    used_count: int = Field(..., ge=0)
    under_maintenance_count: int = Field(..., ge=0)
    required_count: int = Field(..., ge=0)
    notes: Optional[str] = None

class AmbulanceRecordResponse(BaseModel):
    id: int
    date: date
    total_ambulances: int
    available_count: int
    used_count: int
    under_maintenance_count: int
    required_count: int
    source_type: str
    created_by_username: Optional[str]
    created_at: str
    notes: Optional[str]

    class Config:
        from_attributes = True

# Helper functions for integer validations

def validate_non_negative_ints(data_dict: dict, fields: List[str]):
    for field in fields:
        val = data_dict.get(field)
        if val is None:
            raise HTTPException(status_code=400, detail=f"Field '{field}' cannot be missing.")
        if not isinstance(val, int) or isinstance(val, bool):
            raise HTTPException(status_code=400, detail=f"Field '{field}' must be a whole number (integer).")
        if val < 0:
            raise HTTPException(status_code=400, detail=f"Field '{field}' cannot be negative.")

# --- BED ENDPOINTS ---

@router.get("/beds", response_model=List[BedRecordResponse])
def get_beds(db: Session = Depends(get_db)):
    results = db.query(BedRecord).order_by(BedRecord.date.desc(), BedRecord.bed_type.asc()).all()
    
    response_list = []
    for r in results:
        username = r.user.username if r.user else None
        response_list.append({
            "id": r.id,
            "date": r.date,
            "bed_type": r.bed_type,
            "available_count": r.available_count,
            "occupied_count": r.occupied_count,
            "required_count": r.required_count,
            "source_type": r.source_type,
            "created_by_username": username,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return response_list

@router.post("/beds", response_model=BedRecordResponse)
def create_bed_record(
    req: BedRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    # Whole-number checks
    validate_non_negative_ints(req.model_dump(), ["available_count", "occupied_count", "required_count"])

    try:
        parsed_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if req.bed_type not in ["ICU Beds", "General Beds", "Emergency Beds"]:
        raise HTTPException(status_code=400, detail="Invalid bed type category.")

    # Check duplicate
    existing = db.query(BedRecord).filter_by(date=parsed_date, bed_type=req.bed_type).first()
    if existing:
        # Update existing
        existing.available_count = req.available_count
        existing.occupied_count = req.occupied_count
        existing.required_count = req.required_count
        existing.created_by = current_user.id
        db_record = existing
    else:
        # Insert
        db_record = BedRecord(
            date=parsed_date,
            bed_type=req.bed_type,
            available_count=req.available_count,
            occupied_count=req.occupied_count,
            required_count=req.required_count,
            source_type="PLANNER_ENTERED",
            created_by=current_user.id
        )
        db.add(db_record)

    # Automated synchronization to core data_entries table to preserve forecasting workflow compatibility
    resource_map = {
        "ICU Beds": "ICU Demand",
        "General Beds": "General Bed Demand",
        "Emergency Beds": "Emergency Bed Demand"
    }
    
    sync_resource = resource_map[req.bed_type]
    # ICU forecasting model expects occupied beds count, General/ED also track occupied/required
    sync_val = req.occupied_count

    existing_entry = db.query(DataEntry).filter_by(
        date=parsed_date,
        resource=sync_resource,
        source_type="MANUAL_ENTRY"
    ).first()

    if existing_entry:
        existing_entry.value = sync_val
        existing_entry.created_by = current_user.id
    else:
        db.add(DataEntry(
            date=parsed_date,
            resource=sync_resource,
            value=sync_val,
            source_type="MANUAL_ENTRY",
            created_by=current_user.id
        ))

    # Provenance / History Dataset record
    dataset_entry = Dataset(
        filename="Manual Entry",
        source_type="MANUAL_ENTRY",
        uploaded_by=current_user.id,
        resource_type=req.bed_type,
        row_count=1,
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(dataset_entry)

    db.commit()
    db.refresh(db_record)

    return {
        "id": db_record.id,
        "date": db_record.date,
        "bed_type": db_record.bed_type,
        "available_count": db_record.available_count,
        "occupied_count": db_record.occupied_count,
        "required_count": db_record.required_count,
        "source_type": db_record.source_type,
        "created_by_username": current_user.username,
        "created_at": db_record.created_at.isoformat()
    }


# --- OXYGEN ENDPOINTS ---

@router.get("/oxygen", response_model=List[OxygenRecordResponse])
def get_oxygen(db: Session = Depends(get_db)):
    results = db.query(OxygenRecord).order_by(OxygenRecord.date.desc()).all()
    response_list = []
    for r in results:
        username = r.user.username if r.user else None
        response_list.append({
            "id": r.id,
            "date": r.date,
            "total_cylinders": r.total_cylinders,
            "available_cylinders": r.available_cylinders,
            "used_cylinders": r.used_cylinders,
            "filled_refilled": r.filled_refilled,
            "required_cylinders": r.required_cylinders,
            "source_type": r.source_type,
            "created_by_username": username,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "notes": r.notes
        })
    return response_list

@router.post("/oxygen", response_model=OxygenRecordResponse)
def create_oxygen_record(
    req: OxygenRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    validate_non_negative_ints(req.model_dump(), ["total_cylinders", "available_cylinders", "used_cylinders", "filled_refilled", "required_cylinders"])

    try:
        parsed_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    existing = db.query(OxygenRecord).filter_by(date=parsed_date).first()
    if existing:
        existing.total_cylinders = req.total_cylinders
        existing.available_cylinders = req.available_cylinders
        existing.used_cylinders = req.used_cylinders
        existing.filled_refilled = req.filled_refilled
        existing.required_cylinders = req.required_cylinders
        existing.notes = req.notes
        existing.created_by = current_user.id
        db_record = existing
    else:
        db_record = OxygenRecord(
            date=parsed_date,
            total_cylinders=req.total_cylinders,
            available_cylinders=req.available_cylinders,
            used_cylinders=req.used_cylinders,
            filled_refilled=req.filled_refilled,
            required_cylinders=req.required_cylinders,
            source_type="PLANNER_ENTERED",
            created_by=current_user.id,
            notes=req.notes
        )
        db.add(db_record)

    # Sync to data_entries for oxygen
    existing_entry = db.query(DataEntry).filter_by(
        date=parsed_date,
        resource="Oxygen Demand",
        source_type="MANUAL_ENTRY"
    ).first()

    if existing_entry:
        existing_entry.value = req.required_cylinders
        existing_entry.created_by = current_user.id
    else:
        db.add(DataEntry(
            date=parsed_date,
            resource="Oxygen Demand",
            value=req.required_cylinders,
            source_type="MANUAL_ENTRY",
            created_by=current_user.id
        ))

    # Provenance / History Dataset record
    dataset_entry = Dataset(
        filename="Manual Entry",
        source_type="MANUAL_ENTRY",
        uploaded_by=current_user.id,
        resource_type="Oxygen",
        row_count=1,
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(dataset_entry)

    db.commit()
    db.refresh(db_record)

    return {
        "id": db_record.id,
        "date": db_record.date,
        "total_cylinders": db_record.total_cylinders,
        "available_cylinders": db_record.available_cylinders,
        "used_cylinders": db_record.used_cylinders,
        "filled_refilled": db_record.filled_refilled,
        "required_cylinders": db_record.required_cylinders,
        "source_type": db_record.source_type,
        "created_by_username": current_user.username,
        "created_at": db_record.created_at.isoformat(),
        "notes": db_record.notes
    }


# --- BLOOD ENDPOINTS ---

@router.get("/blood", response_model=List[BloodRecordResponse])
def get_blood(db: Session = Depends(get_db)):
    results = db.query(BloodRecord).order_by(BloodRecord.date.desc(), BloodRecord.blood_group.asc()).all()
    response_list = []
    for r in results:
        username = r.user.username if r.user else None
        response_list.append({
            "id": r.id,
            "date": r.date,
            "blood_group": r.blood_group,
            "available_units": r.available_units,
            "used_units": r.used_units,
            "received_units": r.received_units,
            "reserved_units": r.reserved_units,
            "required_units": r.required_units,
            "source_type": r.source_type,
            "created_by_username": username,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return response_list

@router.post("/blood", response_model=BloodRecordResponse)
def create_blood_record(
    req: BloodRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    validate_non_negative_ints(req.model_dump(), ["available_units", "used_units", "received_units", "reserved_units", "required_units"])

    try:
        parsed_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    valid_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    if req.blood_group not in valid_groups:
        raise HTTPException(status_code=400, detail="Invalid blood group category.")

    existing = db.query(BloodRecord).filter_by(date=parsed_date, blood_group=req.blood_group).first()
    if existing:
        existing.available_units = req.available_units
        existing.used_units = req.used_units
        existing.received_units = req.received_units
        existing.reserved_units = req.reserved_units
        existing.required_units = req.required_units
        existing.created_by = current_user.id
        db_record = existing
    else:
        db_record = BloodRecord(
            date=parsed_date,
            blood_group=req.blood_group,
            available_units=req.available_units,
            used_units=req.used_units,
            received_units=req.received_units,
            reserved_units=req.reserved_units,
            required_units=req.required_units,
            source_type="PLANNER_ENTERED",
            created_by=current_user.id
        )
        db.add(db_record)

    # Sync total sum of all blood groups to data_entries for "Blood Demand"
    # Query all blood records for this date
    all_blood_on_date = db.query(BloodRecord).filter_by(date=parsed_date).all()
    # Add new values to sum
    total_required = sum(r.required_units for r in all_blood_on_date if r.blood_group != req.blood_group) + req.required_units

    existing_entry = db.query(DataEntry).filter_by(
        date=parsed_date,
        resource="Blood Demand",
        source_type="MANUAL_ENTRY"
    ).first()

    if existing_entry:
        existing_entry.value = total_required
        existing_entry.created_by = current_user.id
    else:
        db.add(DataEntry(
            date=parsed_date,
            resource="Blood Demand",
            value=total_required,
            source_type="MANUAL_ENTRY",
            created_by=current_user.id
        ))

    # Provenance / History Dataset record
    dataset_entry = Dataset(
        filename="Manual Entry",
        source_type="MANUAL_ENTRY",
        uploaded_by=current_user.id,
        resource_type="Blood",
        row_count=1,
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(dataset_entry)

    db.commit()
    db.refresh(db_record)

    return {
        "id": db_record.id,
        "date": db_record.date,
        "blood_group": db_record.blood_group,
        "available_units": db_record.available_units,
        "used_units": db_record.used_units,
        "received_units": db_record.received_units,
        "reserved_units": db_record.reserved_units,
        "required_units": db_record.required_units,
        "source_type": db_record.source_type,
        "created_by_username": current_user.username,
        "created_at": db_record.created_at.isoformat()
    }


# --- STAFF ENDPOINTS ---

@router.get("/staff", response_model=List[StaffRecordResponse])
def get_staff(db: Session = Depends(get_db)):
    results = db.query(StaffRecord).order_by(StaffRecord.date.desc(), StaffRecord.staff_category.asc()).all()
    response_list = []
    for r in results:
        username = r.user.username if r.user else None
        response_list.append({
            "id": r.id,
            "date": r.date,
            "staff_category": r.staff_category,
            "available_count": r.available_count,
            "assigned_count": r.assigned_count,
            "used_count": r.used_count,
            "required_count": r.required_count,
            "source_type": r.source_type,
            "created_by_username": username,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "shift": r.shift,
            "notes": r.notes
        })
    return response_list

@router.post("/staff", response_model=StaffRecordResponse)
def create_staff_record(
    req: StaffRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    validate_non_negative_ints(req.model_dump(), ["available_count", "assigned_count", "used_count", "required_count"])

    try:
        parsed_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    if req.staff_category not in ["Doctors", "Nurses", "Technicians", "Support Staff"]:
        raise HTTPException(status_code=400, detail="Invalid staff category.")

    existing = db.query(StaffRecord).filter_by(date=parsed_date, staff_category=req.staff_category).first()
    if existing:
        existing.available_count = req.available_count
        existing.assigned_count = req.assigned_count
        existing.used_count = req.used_count
        existing.required_count = req.required_count
        existing.shift = req.shift
        existing.notes = req.notes
        existing.created_by = current_user.id
        db_record = existing
    else:
        db_record = StaffRecord(
            date=parsed_date,
            staff_category=req.staff_category,
            available_count=req.available_count,
            assigned_count=req.assigned_count,
            used_count=req.used_count,
            required_count=req.required_count,
            source_type="PLANNER_ENTERED",
            created_by=current_user.id,
            shift=req.shift,
            notes=req.notes
        )
        db.add(db_record)

    # Sync staff to data_entries for "Staff Requirement"
    # Aggregate required count for all categories
    all_staff_on_date = db.query(StaffRecord).filter_by(date=parsed_date).all()
    total_required = sum(r.required_count for r in all_staff_on_date if r.staff_category != req.staff_category) + req.required_count

    existing_entry = db.query(DataEntry).filter_by(
        date=parsed_date,
        resource="Staff Requirement",
        source_type="MANUAL_ENTRY"
    ).first()

    if existing_entry:
        existing_entry.value = total_required
        existing_entry.created_by = current_user.id
    else:
        db.add(DataEntry(
            date=parsed_date,
            resource="Staff Requirement",
            value=total_required,
            source_type="MANUAL_ENTRY",
            created_by=current_user.id
        ))

    # Provenance / History Dataset record
    dataset_entry = Dataset(
        filename="Manual Entry",
        source_type="MANUAL_ENTRY",
        uploaded_by=current_user.id,
        resource_type="Staff",
        row_count=1,
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(dataset_entry)

    db.commit()
    db.refresh(db_record)

    return {
        "id": db_record.id,
        "date": db_record.date,
        "staff_category": db_record.staff_category,
        "available_count": db_record.available_count,
        "assigned_count": db_record.assigned_count,
        "used_count": db_record.used_count,
        "required_count": db_record.required_count,
        "source_type": db_record.source_type,
        "created_by_username": current_user.username,
        "created_at": db_record.created_at.isoformat(),
        "shift": db_record.shift,
        "notes": db_record.notes
    }


# --- AMBULANCE ENDPOINTS ---

@router.get("/ambulance", response_model=List[AmbulanceRecordResponse])
def get_ambulance(db: Session = Depends(get_db)):
    results = db.query(AmbulanceRecord).order_by(AmbulanceRecord.date.desc()).all()
    response_list = []
    for r in results:
        username = r.user.username if r.user else None
        response_list.append({
            "id": r.id,
            "date": r.date,
            "total_ambulances": r.total_ambulances,
            "available_count": r.available_count,
            "used_count": r.used_count,
            "under_maintenance_count": r.under_maintenance_count,
            "required_count": r.required_count,
            "source_type": r.source_type,
            "created_by_username": username,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "notes": r.notes
        })
    return response_list

@router.post("/ambulance", response_model=AmbulanceRecordResponse)
def create_ambulance_record(
    req: AmbulanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "PLANNER"]))
):
    validate_non_negative_ints(req.model_dump(), ["total_ambulances", "available_count", "used_count", "under_maintenance_count", "required_count"])

    try:
        parsed_date = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    existing = db.query(AmbulanceRecord).filter_by(date=parsed_date).first()
    if existing:
        existing.total_ambulances = req.total_ambulances
        existing.available_count = req.available_count
        existing.used_count = req.used_count
        existing.under_maintenance_count = req.under_maintenance_count
        existing.required_count = req.required_count
        existing.notes = req.notes
        existing.created_by = current_user.id
        db_record = existing
    else:
        db_record = AmbulanceRecord(
            date=parsed_date,
            total_ambulances=req.total_ambulances,
            available_count=req.available_count,
            used_count=req.used_count,
            under_maintenance_count=req.under_maintenance_count,
            required_count=req.required_count,
            source_type="PLANNER_ENTERED",
            created_by=current_user.id,
            notes=req.notes
        )
        db.add(db_record)

    # Sync ambulance to data_entries for "Ambulance Requirement"
    existing_entry = db.query(DataEntry).filter_by(
        date=parsed_date,
        resource="Ambulance Requirement",
        source_type="MANUAL_ENTRY"
    ).first()

    if existing_entry:
        existing_entry.value = req.required_count
        existing_entry.created_by = current_user.id
    else:
        db.add(DataEntry(
            date=parsed_date,
            resource="Ambulance Requirement",
            value=req.required_count,
            source_type="MANUAL_ENTRY",
            created_by=current_user.id
        ))

    # Provenance / History Dataset record
    dataset_entry = Dataset(
        filename="Manual Entry",
        source_type="MANUAL_ENTRY",
        uploaded_by=current_user.id,
        resource_type="Ambulance",
        row_count=1,
        validation_status="VALIDATED",
        processing_status="STORED",
        forecast_status=None
    )
    db.add(dataset_entry)

    db.commit()
    db.refresh(db_record)

    return {
        "id": db_record.id,
        "date": db_record.date,
        "total_ambulances": db_record.total_ambulances,
        "available_count": db_record.available_count,
        "used_count": db_record.used_count,
        "under_maintenance_count": db_record.under_maintenance_count,
        "required_count": db_record.required_count,
        "source_type": db_record.source_type,
        "created_by_username": current_user.username,
        "created_at": db_record.created_at.isoformat(),
        "notes": db_record.notes
    }


# --- GENERAL DELETE ENDPOINT (ADMIN ONLY) ---

@router.delete("/{category}/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource_record(
    category: str,
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    if category == "beds":
        record = db.query(BedRecord).filter_by(id=id).first()
    elif category == "oxygen":
        record = db.query(OxygenRecord).filter_by(id=id).first()
    elif category == "blood":
        record = db.query(BloodRecord).filter_by(id=id).first()
    elif category == "staff":
        record = db.query(StaffRecord).filter_by(id=id).first()
    elif category == "ambulance":
        record = db.query(AmbulanceRecord).filter_by(id=id).first()
    else:
        raise HTTPException(status_code=400, detail="Invalid resource category.")

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    db.delete(record)
    db.commit()
