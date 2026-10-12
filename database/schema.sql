-- Hospital Resource Intelligence Platform Schema
-- PostgreSQL DDL Definitions for Stage 10A / Stage 17 Update

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS recommendations CASCADE;
DROP TABLE IF EXISTS explanations CASCADE;
DROP TABLE IF EXISTS model_metadata CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
DROP TABLE IF EXISTS model_performance CASCADE;
DROP TABLE IF EXISTS forecasts CASCADE;
DROP TABLE IF EXISTS data_entries CASCADE;
DROP TABLE IF EXISTS datasets CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS historical_demand CASCADE;

-- Resource specific operational tables
DROP TABLE IF EXISTS bed_resource_records CASCADE;
DROP TABLE IF EXISTS oxygen_resource_records CASCADE;
DROP TABLE IF EXISTS blood_resource_records CASCADE;
DROP TABLE IF EXISTS staff_resource_records CASCADE;
DROP TABLE IF EXISTS ambulance_resource_records CASCADE;

-- 1. users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT check_user_role CHECK (role IN ('ADMIN', 'PLANNER', 'VIEWER'))
);

-- 2. datasets (batch tracking)
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) DEFAULT NULL,
    source_type VARCHAR(50) NOT NULL,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resource_type VARCHAR(50) DEFAULT NULL,
    row_count INTEGER DEFAULT 0 NOT NULL,
    validation_status VARCHAR(50) NOT NULL,
    processing_status VARCHAR(50) NOT NULL,
    forecast_status VARCHAR(50) DEFAULT NULL,
    CONSTRAINT check_validation_status CHECK (validation_status IN ('VALIDATED', 'FAILED')),
    CONSTRAINT check_processing_status CHECK (processing_status IN ('UPLOADED', 'STORED', 'PROCESSING', 'PROCESSED', 'FAILED')),
    CONSTRAINT check_forecast_status CHECK (forecast_status IN ('FORECAST_GENERATED', 'FAILED') OR forecast_status IS NULL)
);

-- 3. historical_demand
CREATE TABLE historical_demand (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    actual_demand NUMERIC(12, 4) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    CONSTRAINT unique_date_resource UNIQUE (date, resource)
);

-- 4. forecasts
CREATE TABLE forecasts (
    id SERIAL PRIMARY KEY,
    forecast_date DATE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    predicted_demand NUMERIC(12, 4) NOT NULL,
    actual_demand NUMERIC(12, 4),
    model VARCHAR(50) NOT NULL,
    forecast_horizon VARCHAR(20) NOT NULL,
    created_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    CONSTRAINT unique_forecast_date_resource_model UNIQUE (forecast_date, resource, model)
);

-- 5. model_performance
CREATE TABLE model_performance (
    id SERIAL PRIMARY KEY,
    model VARCHAR(50) NOT NULL,
    target VARCHAR(50) NOT NULL,
    mae NUMERIC(12, 6) NOT NULL,
    rmse NUMERIC(12, 6) NOT NULL,
    mape NUMERIC(12, 6),
    evaluation_period VARCHAR(100) NOT NULL,
    rank INTEGER NOT NULL,
    evaluation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT unique_model_target UNIQUE (model, target)
);

-- 6. alerts
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_date DATE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    predicted_demand NUMERIC(12, 4) NOT NULL,
    actual_capacity NUMERIC(12, 4) DEFAULT NULL,
    simulated_capacity NUMERIC(12, 4) NOT NULL,
    is_capacity_simulated BOOLEAN DEFAULT TRUE NOT NULL,
    capacity_gap NUMERIC(12, 4) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    reason TEXT NOT NULL,
    CONSTRAINT unique_alert_date_resource UNIQUE (alert_date, resource),
    CONSTRAINT check_risk_level CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- 7. recommendations
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    recommendation TEXT NOT NULL,
    trigger TEXT NOT NULL,
    model VARCHAR(50) NOT NULL,
    CONSTRAINT unique_rec_date_resource UNIQUE (date, resource),
    CONSTRAINT check_rec_risk_level CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- 8. explanations
CREATE TABLE explanations (
    id SERIAL PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    model VARCHAR(50) NOT NULL,
    feature VARCHAR(100) NOT NULL,
    feature_value NUMERIC(12, 4) NOT NULL,
    contribution NUMERIC(12, 6) NOT NULL,
    direction INTEGER NOT NULL,
    explanation_method VARCHAR(10) NOT NULL,
    CONSTRAINT unique_explanation UNIQUE (resource, date, model, feature, explanation_method),
    CONSTRAINT check_direction CHECK (direction IN (-1, 1)),
    CONSTRAINT check_explanation_method CHECK (explanation_method IN ('SHAP', 'LIME'))
);

-- 9. model_metadata
CREATE TABLE model_metadata (
    id SERIAL PRIMARY KEY,
    model VARCHAR(50) NOT NULL,
    target VARCHAR(50) NOT NULL,
    metadata_type VARCHAR(50) NOT NULL,
    feature VARCHAR(100) DEFAULT NULL,
    value NUMERIC(12, 6) DEFAULT NULL,
    json_data JSONB DEFAULT NULL,
    created_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT unique_metadata_entry UNIQUE (model, target, metadata_type, feature)
);

-- 10. data_entries
CREATE TABLE data_entries (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    resource VARCHAR(50) NOT NULL,
    value NUMERIC(12, 4) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    CONSTRAINT unique_date_resource_source UNIQUE (date, resource, source_type),
    CONSTRAINT check_source_type CHECK (source_type IN ('ORIGINAL_DATASET', 'UPLOADED_DATASET', 'MANUAL_ENTRY', 'SIMULATED'))
);

-- 11. bed_resource_records
CREATE TABLE bed_resource_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    bed_type VARCHAR(20) NOT NULL,
    available_count INTEGER NOT NULL,
    occupied_count INTEGER NOT NULL,
    required_count INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 12. oxygen_resource_records
CREATE TABLE oxygen_resource_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_cylinders INTEGER NOT NULL,
    available_cylinders INTEGER NOT NULL,
    used_cylinders INTEGER NOT NULL,
    filled_refilled INTEGER NOT NULL,
    required_cylinders INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    notes TEXT
);

-- 13. blood_resource_records
CREATE TABLE blood_resource_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    available_units INTEGER NOT NULL,
    used_units INTEGER NOT NULL,
    received_units INTEGER NOT NULL,
    reserved_units INTEGER NOT NULL,
    required_units INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 14. staff_resource_records
CREATE TABLE staff_resource_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    staff_category VARCHAR(30) NOT NULL,
    available_count INTEGER NOT NULL,
    assigned_count INTEGER NOT NULL,
    used_count INTEGER NOT NULL,
    required_count INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    shift VARCHAR(20),
    notes TEXT
);

-- 15. ambulance_resource_records
CREATE TABLE ambulance_resource_records (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_ambulances INTEGER NOT NULL,
    available_count INTEGER NOT NULL,
    used_count INTEGER NOT NULL,
    under_maintenance_count INTEGER NOT NULL,
    required_count INTEGER NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    notes TEXT
);

-- Create Indexes for Performance Optimization
CREATE INDEX idx_historical_date_res ON historical_demand(date, resource);
CREATE INDEX idx_forecast_date_res ON forecasts(forecast_date, resource);
CREATE INDEX idx_alerts_date_res ON alerts(alert_date, resource);
CREATE INDEX idx_explanations_lookup ON explanations(resource, date, model);
CREATE INDEX idx_metadata_lookup ON model_metadata(model, target);
CREATE INDEX idx_data_entries_lookup ON data_entries(date, resource);
CREATE INDEX idx_datasets_status ON datasets(validation_status, processing_status);
CREATE INDEX idx_beds_lookup ON bed_resource_records(date, bed_type);
CREATE INDEX idx_oxygen_lookup ON oxygen_resource_records(date);
CREATE INDEX idx_blood_lookup ON blood_resource_records(date, blood_group);
CREATE INDEX idx_staff_lookup ON staff_resource_records(date, staff_category);
CREATE INDEX idx_ambulance_lookup ON ambulance_resource_records(date);
