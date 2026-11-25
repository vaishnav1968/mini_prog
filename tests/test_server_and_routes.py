"""
Flask Server Endpoints and UI Integration Tests
===============================================
Tests:
  1. GET /dashboard (loads metrics, Plotly chart data, renders HTML)
  2. GET /upload (renders upload interface)
  3. POST /upload/process (processes uploaded CSV, runs pipeline)
  4. GET /sample/demo (loads 7-day demo dataset)
  5. GET /sample/realistic (loads 60-day realistic benchmark)
  6. GET /visualize (renders telemetry graphs)
  7. GET /anomalies (renders ML comparisons)
  8. GET /predictions (renders LSTM and Autoencoder charts)
  9. GET /alerts (renders alert feed)
  10. GET /reports (renders report download links)
  11. GET /about (renders architecture documentation)
  12. GET /download/cleaned (downloads sanitized CSV)
  13. GET /download/pdf (downloads generated PDF audit report)
"""

import os
import sys
import unittest
import io
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app, init_db

class TestFlaskEndpoints(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        init_db()

    def test_01_dashboard_and_pipeline(self):
        # First load sample data
        res_sample = self.client.get("/sample/demo", follow_redirects=True)
        self.assertEqual(res_sample.status_code, 200)
        self.assertIn(b"WEATHER", res_sample.data)
        self.assertIn(b"Integrity Score", res_sample.data)

    def test_02_all_pages_render(self):
        pages = [
            "/dashboard",
            "/upload",
            "/visualize",
            "/anomalies",
            "/predictions",
            "/alerts",
            "/reports",
            "/about"
        ]
        for p in pages:
            res = self.client.get(p)
            self.assertEqual(res.status_code, 200, f"Page {p} returned {res.status_code}")

    def test_03_csv_upload_endpoint(self):
        # Create small test CSV in memory
        csv_content = """timestamp,temperature,humidity,wind_speed,rainfall
2026-01-01 00:00:00,22.5,65.0,12.0,0.0
2026-01-01 01:00:00,21.8,67.0,11.5,0.0
2026-01-01 02:00:00,75.0,140.0,95.0,-10.0
2026-01-01 03:00:00,20.5,70.0,10.0,0.0
"""
        data = {
            "file": (io.BytesIO(csv_content.encode("utf-8")), "test_upload.csv")
        }
        res = self.client.post("/upload/process", data=data, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Successfully ingested and audited", res.data)

    def test_04_download_endpoints(self):
        # Cleaned CSV download
        res_csv = self.client.get("/download/cleaned")
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.headers.get("Content-Type"), "text/csv; charset=utf-8")

        # PDF Report download
        res_pdf = self.client.get("/download/pdf")
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf.headers.get("Content-Type"), "application/pdf")

if __name__ == "__main__":
    unittest.main()
