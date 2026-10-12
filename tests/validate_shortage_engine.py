import unittest
import pandas as pd
import numpy as np
import os
import sys

# Add parent directories to imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ml/decision_engine')))

import thresholds
from shortage_detector import validate_inputs, detect_icu_shortages, detect_ed_pressure

class TestShortageEngine(unittest.TestCase):
    
    def setUp(self):
        # Sample valid DataFrame
        self.valid_df = pd.DataFrame({
            'date': pd.date_range(start='2026-08-28', periods=7),
            'predicted': [1.0, 1.2, 1.5, 1.7, 1.8, 1.9, 2.0]
        })
        
    def test_validation_correct_horizon(self):
        # Exactly 7 rows should pass
        try:
            validate_inputs(self.valid_df)
        except ValueError as e:
            self.fail(f"validate_inputs failed on valid data: {e}")
            
    def test_validation_incorrect_horizon(self):
        invalid_df = pd.DataFrame({
            'date': pd.date_range(start='2026-08-28', periods=6),
            'predicted': [1.0]*6
        })
        with self.assertRaises(ValueError):
            validate_inputs(invalid_df)
            
    def test_validation_negative_values(self):
        invalid_df = self.valid_df.copy()
        invalid_df.loc[3, 'predicted'] = -0.5
        with self.assertRaises(ValueError):
            validate_inputs(invalid_df)
            
    def test_validation_duplicate_dates(self):
        invalid_df = self.valid_df.copy()
        invalid_df.loc[1, 'date'] = invalid_df.loc[0, 'date']
        with self.assertRaises(ValueError):
            validate_inputs(invalid_df)

    def test_risk_mapping_low(self):
        # Capacity is 2.0. Demand of 1.0 is 50% (LOW)
        test_df = pd.DataFrame({
            'date': pd.date_range(start='2026-08-28', periods=7),
            'predicted': [1.0]*7
        })
        # Save temp forecast
        temp_path = "temp_test_icu.csv"
        test_df.to_csv(temp_path, index=False)
        
        # Override threshold parameter temporarily
        thresholds.ICU_CAPACITY = 2.0
        df_alerts = detect_icu_shortages(temp_path)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        self.assertTrue((df_alerts['risk_level'] == 'LOW').all())
        
    def test_risk_mapping_medium(self):
        # Capacity is 2.0. Demand of 1.9 is 95% (MEDIUM)
        test_df = pd.DataFrame({
            'date': pd.date_range(start='2026-08-28', periods=7),
            'predicted': [1.9]*7
        })
        temp_path = "temp_test_icu.csv"
        test_df.to_csv(temp_path, index=False)
        
        thresholds.ICU_CAPACITY = 2.0
        thresholds.ICU_MEDIUM_PCT = 0.90
        df_alerts = detect_icu_shortages(temp_path)
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        self.assertTrue((df_alerts['risk_level'] == 'MEDIUM').all())
        
    def test_risk_mapping_high(self):
        # Capacity is 2.0. Demand of 2.1 is 105% (HIGH)
        test_df = pd.DataFrame({
            'date': pd.date_range(start='2026-08-28', periods=7),
            'predicted': [2.1]*7
        })
        temp_path = "temp_test_icu.csv"
        test_df.to_csv(temp_path, index=False)
        
        thresholds.ICU_CAPACITY = 2.0
        df_alerts = detect_icu_shortages(temp_path)
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        self.assertTrue((df_alerts['risk_level'] == 'HIGH').all())
        
    def test_missing_capacity(self):
        # Set capacity to None or invalid to test exception
        thresholds.ICU_CAPACITY = None
        test_df = pd.DataFrame({
            'date': pd.date_range(start='2026-08-28', periods=7),
            'predicted': [1.0]*7
        })
        temp_path = "temp_test_icu.csv"
        test_df.to_csv(temp_path, index=False)
        
        with self.assertRaises(ValueError):
            detect_icu_shortages(temp_path)
            
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        # Reset capacity to original simulation value
        thresholds.ICU_CAPACITY = 2.0

if __name__ == "__main__":
    unittest.main()
