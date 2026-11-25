"""
Unit and Integration Tests for AI-Based Weather Data Integrity System
====================================================================
Tests:
  1. Data Preprocessing & Physical Constraint Checking
  2. Imputation of Missing Values & Freeze Detection
  3. Machine Learning Models (Isolation Forest, LOF, Z-Score)
  4. Deep Learning Sequence Preparation & Modeling
  5. Data Integrity Validator & Weighted Scoring
  6. Alert Generation & Severity Mapping
  7. Database Schema & Persistence
  8. Report Generation (CSV & PDF)
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import Modules
from preprocessing.cleaning import WeatherDataPreprocessor
from models.isolation_forest import WeatherIsolationForest
from models.lof_model import WeatherLOF
from models.zscore_model import WeatherZScoreDetector
from integrity.validator import DataIntegrityValidator
from alerts.alert_manager import AlertManager
from database.db import init_db, save_analysis_run, get_recent_datasets
from reports.report_generator import export_cleaned_csv, generate_pdf_report

class TestWeatherIntegritySystem(unittest.TestCase):
    def setUp(self):
        """Create synthetic test DataFrame with deliberate anomalies."""
        timestamps = [
            (datetime(2026, 1, 1, 0, 0) + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S")
            for i in range(100)
        ]
        # Realistic diurnal temperature
        hours = np.array([i % 24 for i in range(100)])
        temps = 20.0 + 5.0 * np.sin((hours - 8) * (2 * np.pi / 24))
        hums = 60.0 - (temps - 20.0) * 2.0
        winds = np.random.uniform(5.0, 20.0, 100)
        rain = np.zeros(100)

        # Inject anomalies
        temps[10] = 75.0      # Physical temperature impossibility (>60C)
        hums[20] = 140.0      # Physical humidity impossibility (>100%)
        rain[30] = -5.0       # Physical negative rainfall (<0mm)
        temps[40:55] = 22.4   # Stuck sensor (frozen for 15 hours)
        temps[60] = np.nan    # Missing value

        self.test_df = pd.DataFrame({
            "timestamp": timestamps,
            "temperature": temps,
            "humidity": hums,
            "wind_speed": winds,
            "rainfall": rain,
            "sensor_id": "STATION_TEST_01"
        })

    def test_01_preprocessing_and_cleaning(self):
        preprocessor = WeatherDataPreprocessor()
        cleaned, log = preprocessor.clean_and_impute(self.test_df)
        
        # Check missing values imputed
        self.assertEqual(cleaned["temperature"].isnull().sum(), 0)
        # Check physical limit violations flagged
        self.assertTrue("temperature_raw" in cleaned.columns)
        self.assertEqual(cleaned.loc[10, "temperature_raw"], 75.0)
        # Check frozen sensor detected
        self.assertTrue("temperature_is_frozen" in cleaned.columns)
        self.assertTrue(cleaned["temperature_is_frozen"].any())

    def test_02_machine_learning_models(self):
        preprocessor = WeatherDataPreprocessor()
        cleaned, _ = preprocessor.clean_and_impute(self.test_df)

        # 1. Isolation Forest
        iso = WeatherIsolationForest(contamination=0.05)
        _, _, df_iso = iso.fit_predict(cleaned)
        self.assertIn("iso_forest_anomaly", df_iso.columns)
        self.assertGreater(df_iso["iso_forest_anomaly"].sum(), 0)

        # 2. Local Outlier Factor
        lof = WeatherLOF(contamination=0.05)
        _, _, df_lof = lof.fit_predict(df_iso)
        self.assertIn("lof_anomaly", df_lof.columns)

        # 3. Z-Score
        zscore = WeatherZScoreDetector(threshold=2.5)
        df_z = zscore.detect(df_lof)
        self.assertIn("zscore_anomaly", df_z.columns)

    def test_03_integrity_validation_and_scoring(self):
        preprocessor = WeatherDataPreprocessor()
        cleaned, _ = preprocessor.clean_and_impute(self.test_df)

        iso = WeatherIsolationForest(contamination=0.05)
        _, _, df_iso = iso.fit_predict(cleaned)
        lof = WeatherLOF(contamination=0.05)
        _, _, df_lof = lof.fit_predict(df_iso)
        zscore = WeatherZScoreDetector(threshold=2.5)
        df_ml = zscore.detect(df_lof)

        validator = DataIntegrityValidator()
        eval_df = validator.evaluate_dataset(df_ml, raw_df=self.test_df)
        metrics = validator.get_integrity_metrics(eval_df)

        self.assertIn("integrity_score", eval_df.columns)
        self.assertIn("integrity_status", eval_df.columns)
        # Record 10 had 75C temp (severe violation), score should be penalized
        self.assertLess(eval_df.loc[10, "integrity_score"], 80)
        self.assertEqual(eval_df.loc[10, "integrity_status"], "CORRUPTED_OR_TAMPERED")
        self.assertIn("integrity_percentage", metrics)

    def test_04_alerts_generation(self):
        preprocessor = WeatherDataPreprocessor()
        cleaned, _ = preprocessor.clean_and_impute(self.test_df)
        iso = WeatherIsolationForest(contamination=0.05)
        _, _, df_iso = iso.fit_predict(cleaned)
        validator = DataIntegrityValidator()
        eval_df = validator.evaluate_dataset(df_iso, raw_df=self.test_df)

        alert_mgr = AlertManager()
        alerts = alert_mgr.generate_alerts_from_evaluation(eval_df)
        self.assertGreater(len(alerts), 0)
        
        # Check severity exists
        severities = {a["severity"] for a in alerts}
        self.assertTrue("CRITICAL" in severities or "HIGH" in severities)

    def test_05_database_persistence(self):
        init_db()
        preprocessor = WeatherDataPreprocessor()
        cleaned, _ = preprocessor.clean_and_impute(self.test_df)
        validator = DataIntegrityValidator()
        eval_df = validator.evaluate_dataset(cleaned, raw_df=self.test_df)
        metrics = validator.get_integrity_metrics(eval_df)
        alert_mgr = AlertManager()
        alerts = alert_mgr.generate_alerts_from_evaluation(eval_df)

        ds_id = save_analysis_run("test_unit_run.csv", eval_df, metrics, alerts)
        self.assertIsInstance(ds_id, int)
        recents = get_recent_datasets(5)
        self.assertTrue(len(recents) > 0)

    def test_06_report_generation(self):
        preprocessor = WeatherDataPreprocessor()
        cleaned, _ = preprocessor.clean_and_impute(self.test_df)
        validator = DataIntegrityValidator()
        eval_df = validator.evaluate_dataset(cleaned, raw_df=self.test_df)
        metrics = validator.get_integrity_metrics(eval_df)
        alerts = [{"id": 1, "timestamp": "2026-01-01 10:00:00", "severity": "CRITICAL", "parameter": "Temperature", "detected_value": "75.0°C", "reference_range": "-50 to 60°C", "reason": "Physical limit violation"}]

        csv_out = "data/processed/test_clean_export.csv"
        pdf_out = "reports/test_integrity_report.pdf"

        export_cleaned_csv(eval_df, csv_out)
        self.assertTrue(os.path.exists(csv_out))

        generate_pdf_report("test_unit_run.csv", metrics, alerts, pdf_out)
        self.assertTrue(os.path.exists(pdf_out))

if __name__ == "__main__":
    unittest.main()
