from sqlalchemy import Column, Integer, String, Numeric, Date, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from backend.database import Base

class HistoricalDemand(Base):
    __tablename__ = "historical_demand"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    resource = Column(String(50), nullable=False)
    actual_demand = Column(Numeric(12, 4), nullable=False)
    target_type = Column(String(50), nullable=False)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=True)
    source_type = Column(String(50), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    resource_type = Column(String(50), nullable=True)
    row_count = Column(Integer, default=0, nullable=False)
    validation_status = Column(String(50), nullable=False)
    processing_status = Column(String(50), nullable=False)
    forecast_status = Column(String(50), nullable=True)

    user = relationship("User")


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    forecast_date = Column(Date, nullable=False)
    resource = Column(String(50), nullable=False)
    predicted_demand = Column(Numeric(12, 4), nullable=False)
    actual_demand = Column(Numeric(12, 4), nullable=True)
    model = Column(String(50), nullable=False)
    forecast_horizon = Column(String(20), nullable=False)
    created_timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)

    dataset = relationship("Dataset")


class ModelPerformance(Base):
    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(50), nullable=False)
    target = Column(String(50), nullable=False)
    mae = Column(Numeric(12, 6), nullable=False)
    rmse = Column(Numeric(12, 6), nullable=False)
    mape = Column(Numeric(12, 6), nullable=True)
    evaluation_period = Column(String(100), nullable=False)
    rank = Column(Integer, nullable=False)
    evaluation_timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_date = Column(Date, nullable=False)
    resource = Column(String(50), nullable=False)
    predicted_demand = Column(Numeric(12, 4), nullable=False)
    actual_capacity = Column(Numeric(12, 4), default=None, nullable=True)
    simulated_capacity = Column(Numeric(12, 4), nullable=False)
    is_capacity_simulated = Column(Boolean, default=True, nullable=False)
    capacity_gap = Column(Numeric(12, 4), nullable=False)
    risk_level = Column(String(10), nullable=False)
    reason = Column(Text, nullable=False)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)
    date = Column(Date, nullable=False)
    resource = Column(String(50), nullable=False)
    risk_level = Column(String(10), nullable=False)
    recommendation = Column(Text, nullable=False)
    trigger = Column(Text, nullable=False)
    model = Column(String(50), nullable=False)

    # Establish the relationship
    alert = relationship("Alert", backref="recommendations")


class Explanation(Base):
    __tablename__ = "explanations"

    id = Column(Integer, primary_key=True, index=True)
    resource = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    model = Column(String(50), nullable=False)
    feature = Column(String(100), nullable=False)
    feature_value = Column(Numeric(12, 4), nullable=False)
    contribution = Column(Numeric(12, 6), nullable=False)
    direction = Column(Integer, nullable=False)
    explanation_method = Column(String(10), nullable=False)


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True)
    model = Column(String(50), nullable=False)
    target = Column(String(50), nullable=False)
    metadata_type = Column(String(50), nullable=False)
    feature = Column(String(100), default=None, nullable=True)
    value = Column(Numeric(12, 6), default=None, nullable=True)
    json_data = Column(JSON, default=None, nullable=True)
    created_timestamp = Column(DateTime(timezone=True), default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)


class DataEntry(Base):
    __tablename__ = "data_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    resource = Column(String(50), nullable=False, index=True)
    value = Column(Numeric(12, 4), nullable=False)
    source_type = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User")
    dataset = relationship("Dataset")


class BedRecord(Base):
    __tablename__ = "bed_resource_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    bed_type = Column(String(20), nullable=False)
    available_count = Column(Integer, nullable=False)
    occupied_count = Column(Integer, nullable=False)
    required_count = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    user = relationship("User")


class OxygenRecord(Base):
    __tablename__ = "oxygen_resource_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    total_cylinders = Column(Integer, nullable=False)
    available_cylinders = Column(Integer, nullable=False)
    used_cylinders = Column(Integer, nullable=False)
    filled_refilled = Column(Integer, nullable=False)
    required_cylinders = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    user = relationship("User")


class BloodRecord(Base):
    __tablename__ = "blood_resource_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    blood_group = Column(String(5), nullable=False)
    available_units = Column(Integer, nullable=False)
    used_units = Column(Integer, nullable=False)
    received_units = Column(Integer, nullable=False)
    reserved_units = Column(Integer, nullable=False)
    required_units = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    user = relationship("User")


class StaffRecord(Base):
    __tablename__ = "staff_resource_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    staff_category = Column(String(30), nullable=False)
    available_count = Column(Integer, nullable=False)
    assigned_count = Column(Integer, nullable=False)
    used_count = Column(Integer, nullable=False)
    required_count = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    shift = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User")


class AmbulanceRecord(Base):
    __tablename__ = "ambulance_resource_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    total_ambulances = Column(Integer, nullable=False)
    available_count = Column(Integer, nullable=False)
    used_count = Column(Integer, nullable=False)
    under_maintenance_count = Column(Integer, nullable=False)
    required_count = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    user = relationship("User")

