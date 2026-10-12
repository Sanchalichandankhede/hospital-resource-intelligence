#!/usr/bin/env python3
"""
validate_database_schema.py
Unit test suite to validate the integrity of schema.sql declarations.
"""

import os
import re
import sys

SCHEMA_PATH = "database/schema.sql"

def main():
    print("==================================================")
    print("DATABASE SCHEMA DDL INTEGRITY CHECK")
    print("==================================================")

    if not os.path.exists(SCHEMA_PATH):
        print(f"Error: Schema script not found at {SCHEMA_PATH}")
        sys.exit(1)

    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()

    # Normalize text by removing comments and converting multiple spaces to single spaces
    sql_clean = re.sub(r"--.*", "", sql)
    sql_clean = re.sub(r"\s+", " ", sql_clean).strip().lower()

    required_tables = [
        "historical_demand",
        "forecasts",
        "model_performance",
        "alerts",
        "recommendations",
        "explanations",
        "model_metadata"
    ]

    errors = []

    # 1. Verify all required tables exist
    print("1. Checking table declarations...")
    for table in required_tables:
        match = re.search(rf"create\s+table\s+{table}\b", sql_clean)
        if match:
            print(f"  [PASS] Table '{table}' is defined.")
        else:
            errors.append(f"Missing table declaration: '{table}'")
            print(f"  [FAIL] Table '{table}' is NOT defined!")

    # 2. Check for Primary Keys in each table
    print("\n2. Checking Primary Key definitions...")
    for table in required_tables:
        # Match table block content
        block_match = re.search(rf"create\s+table\s+{table}\s*\((.*?)\)\s*;", sql_clean)
        if block_match:
            columns_def = block_match.group(1)
            if "primary key" in columns_def:
                print(f"  [PASS] Primary Key exists for table '{table}'.")
            else:
                errors.append(f"Missing Primary Key for table: '{table}'")
                print(f"  [FAIL] Table '{table}' does NOT define a Primary Key!")
        else:
            print(f"  [SKIP] Table '{table}' block could not be extracted.")

    # 3. Verify Foreign Keys
    print("\n3. Checking Foreign Key relationships...")
    # Check that recommendations.alert_id references alerts(id)
    rec_block = re.search(r"create\s+table\s+recommendations\s*\((.*?)\)\s*;", sql_clean)
    if rec_block:
        defs = rec_block.group(1)
        if "references alerts" in defs or "references alerts(id)" in defs:
            print("  [PASS] Foreign Key 'recommendations -> alerts' is defined.")
        else:
            errors.append("Missing Foreign Key relationship: recommendations.alert_id -> alerts(id)")
            print("  [FAIL] recommendations does NOT define a Foreign Key referencing alerts!")
    else:
        print("  [SKIP] recommendations table block not found.")

    # 4. Verify Constraints (check constraints and unique clauses)
    print("\n4. Checking check constraints and unique index rules...")
    # Check constraint on alerts risk level
    if "check (risk_level in ('low', 'medium', 'high', 'critical'))" in sql_clean or "check(risk_level in ('low', 'medium', 'high', 'critical'))" in sql_clean:
        print("  [PASS] Check constraint 'risk_level' is defined in alerts.")
    else:
        errors.append("Missing Check Constraint on alerts.risk_level")
        print("  [FAIL] Check constraint on alerts.risk_level NOT found!")

    # Check constraint on direction in explanations
    if "check (direction in (-1, 1))" in sql_clean or "check(direction in (-1, 1))" in sql_clean:
        print("  [PASS] Check constraint 'direction' is defined in explanations.")
    else:
        errors.append("Missing Check Constraint on explanations.direction")
        print("  [FAIL] Check constraint on explanations.direction NOT found!")

    # Check constraint on explanation method
    if "check (explanation_method in ('shap', 'lime'))" in sql_clean or "check(explanation_method in ('shap', 'lime'))" in sql_clean:
        print("  [PASS] Check constraint 'explanation_method' is defined in explanations.")
    else:
        errors.append("Missing Check Constraint on explanations.explanation_method")
        print("  [FAIL] Check constraint on explanations.explanation_method NOT found!")

    # 5. Verify simulated capacity constraints
    print("\n5. Checking Simulated Capacity columns and safeguards...")
    alerts_block = re.search(r"create\s+table\s+alerts\s*\((.*?)\)\s*;", sql_clean)
    if alerts_block:
        defs = alerts_block.group(1)
        if "actual_capacity" in defs and "simulated_capacity" in defs and "is_capacity_simulated" in defs:
            print("  [PASS] Simulated capacity safeguard columns are defined in alerts.")
        else:
            errors.append("Missing capacity safeguard columns in alerts table")
            print("  [FAIL] alerts table does NOT define simulated_capacity or actual_capacity columns!")
    else:
        print("  [SKIP] alerts table block not found.")

    # 6. Verify that no insert statements exist
    print("\n6. Checking for database seeding code safeguards...")
    if "insert into" in sql_clean:
        errors.append("Schema script must not contain INSERT statements to prevent mock data injection.")
        print("  [FAIL] Schema contains INSERT statements!")
    else:
        print("  [PASS] No data insertion commands found in DDL script.")

    print("\n==================================================")
    print("VERIFICATION SUMMARY")
    print("==================================================")
    if len(errors) == 0:
        print("ALL TESTS PASSED SUCCESSFULLY! Schema definition is valid.")
        sys.exit(0)
    else:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
