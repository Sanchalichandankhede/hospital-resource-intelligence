# Data Gaps Analysis

This document identifies resources that are outside the current scope of the **Hospital Resource Intelligence and Optimization Platform** due to lack of adequate raw data. It details why they are currently unsupported and outlines the specific datasets and columns that would be required to support them in a future version.

---

## 1. Oxygen Forecasting
* **Current Status:** Not Supported.
* **Why it's a Gap:** The current datasets (NHS Beds and MIMIC-IV Stays) contain beds capacity and general occupancy. They do not record oxygen consumption rates, oxygen supply tank levels, flow rates, or patient-level respiratory support details (ventilators, nasal cannulas) in a consolidated format.
* **Required Dataset Structure if Implemented:**
  - **Source:** Hospital Biomedical Engineering or Facility Management systems.
  - **Frequency:** Hourly or Daily.
  - **Proposed Columns:**
    - `timestamp` (datetime): Time of recording.
    - `oxygen_tank_level_psi` (float): Current main tank pressure.
    - `oxygen_flow_rate_lpm` (float): Total liquid oxygen flow rate in liters per minute.
    - `ventilator_active_count` (int): Number of mechanical ventilators currently active.
    - `high_flow_nasal_cannula_count` (int): Number of active HFNC machines.
    - `daily_oxygen_cylinder_replacements` (int): Number of cylinders swapped.
    - `daily_liquid_oxygen_refills_liters` (float): Volumetric refill amount.

---

## 2. Blood-Unit Inventory Forecasting
* **Current Status:** Not Supported.
* **Why it's a Gap:** The current datasets do not contain blood bank inventory records, transfusions, donations, or blood component classifications (packed red blood cells, platelets, fresh frozen plasma).
* **Required Dataset Structure if Implemented:**
  - **Source:** Hospital Blood Bank Management System (BBMS).
  - **Frequency:** Daily.
  - **Proposed Columns:**
    - `date` (date): Date of inventory check.
    - `blood_type` (categorical: A+, A-, B+, B-, AB+, AB-, O+, O-).
    - `component_type` (categorical: PRBC, Platelets, FFP, Cryoprecipitate).
    - `units_in_stock` (int): Number of viable units available.
    - `units_transfused` (int): Units consumed by patients on that day.
    - `units_donated_received` (int): Units added through donations or supply shipments.
    - `units_expired_discarded` (int): Units wasted due to expiration.

---

## 3. Medicine Inventory Forecasting
* **Current Status:** Not Supported.
* **Why it's a Gap:** The clinical demo dataset contains prescriptions, but they are sparse and do not contain pharmacy stock levels, supply-chain reorder points, batch expiration dates, or daily pharmacy dispensing logs.
* **Required Dataset Structure if Implemented:**
  - **Source:** Hospital Pharmacy Information System (PIS) or ERP.
  - **Frequency:** Daily.
  - **Proposed Columns:**
    - `date` (date): Date of recording.
    - `drug_id` / `drug_name` (string): Unique identifier for the medication.
    - `dosage_form` (categorical: Injection, Tablet, Syrup).
    - `current_stock_quantity` (int): Number of units in stock.
    - `units_dispensed` (int): Number of units distributed to wards.
    - `reorder_threshold` (int): Safety stock level.
    - `units_ordered_pending` (int): Outstanding supplier orders.

---

## 4. Staff Forecasting (Physicians & Nurses)
* **Current Status:** Not Supported.
* **Why it's a Gap:** No human resources, roster scheduling, shift schedules, nurse-to-patient ratios, or clinical staff attendance records are present in the provided datasets.
* **Required Dataset Structure if Implemented:**
  - **Source:** Hospital Human Resource Management (HRM) and Rostering System.
  - **Frequency:** Shift-level (typically 8 or 12 hours) or Daily.
  - **Proposed Columns:**
    - `shift_id` (string): Unique ID for the shift.
    - `date` (date): Roster date.
    - `department` (categorical: ICU, ED, General Ward).
    - `staff_role` (categorical: Nurse, Resident, Attending, Respiratory Therapist).
    - `scheduled_staff_count` (int): Number of staff scheduled.
    - `actual_staff_present_count` (int): Staff who checked in.
    - `overtime_hours_logged` (float): Total overtime hours worked during the shift.
    - `absenteeism_rate` (float): Percentage of scheduled staff who called in sick.
