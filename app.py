"""
AI-Based Weather Data Integrity System - Flask Application
==========================================================
Main Web Server & Pipeline Orchestrator.
Integrates:
  - Weather Data Ingestion (CSV & API ready)
  - Data Preprocessing & Validation
  - ML Anomaly Detection (Isolation Forest, LOF, Z-Score)
  - Deep Learning Models (LSTM & Autoencoders)
  - Integrity Validator & Scoring
  - Alert Management System
  - SQLite Database Storage
  - PDF & CSV Report Generators
"""

import os
import io
import json
import numpy as np
import pandas as pd
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, send_file, jsonify, session
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Database
from database.db import init_db, save_analysis_run, get_recent_datasets, get_recent_alerts
init_db()

# Import Processing & AI Modules
from preprocessing.cleaning import WeatherDataPreprocessor
from models.isolation_forest import WeatherIsolationForest
from models.lof_model import WeatherLOF
from models.zscore_model import WeatherZScoreDetector
from models.lstm_model import WeatherLSTMPredictor
from models.autoencoder import WeatherAutoencoder
from integrity.validator import DataIntegrityValidator
from alerts.alert_manager import AlertManager
from reports.report_generator import export_cleaned_csv, generate_pdf_report

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "weather-integrity-secret-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload
app.config["UPLOAD_FOLDER"] = "data/raw"

# Global in-memory cache for the actively analyzed session dataset
ACTIVE_DATA = {
    "filename": "weather_sample_realistic.csv",
    "evaluated_df": None,
    "metrics": {},
    "iso_summary": {},
    "lof_summary": {},
    "zscore_summary": {},
    "lstm_summary": {},
    "autoenc_summary": {},
    "alerts": []
}

def run_full_integrity_pipeline(df: pd.DataFrame, filename: str = "dataset.csv"):
    """Orchestrates complete end-to-end preprocessing, ML, DL, and Integrity validation."""
    preprocessor = WeatherDataPreprocessor()
    iso_model = WeatherIsolationForest(contamination=0.04)
    lof_model = WeatherLOF(contamination=0.04)
    zscore_detector = WeatherZScoreDetector(threshold=3.0)
    lstm_predictor = WeatherLSTMPredictor(sequence_length=24, epochs=10)
    autoencoder = WeatherAutoencoder(latent_dim=2, epochs=15)
    validator = DataIntegrityValidator()
    alert_mgr = AlertManager()

    # Step 1: Preprocessing & Imputation
    cleaned_df, cleaning_log = preprocessor.clean_and_impute(df)

    # Step 2: Machine Learning Models
    _, _, df_iso = iso_model.fit_predict(cleaned_df)
    _, _, df_lof = lof_model.fit_predict(df_iso)
    df_ml = zscore_detector.detect(df_lof)

    iso_sum = iso_model.get_summary(df_ml)
    lof_sum = lof_model.get_summary(df_ml)
    zscore_sum = zscore_detector.get_summary(df_ml)

    # Step 3: Deep Learning Models
    df_lstm, lstm_sum = lstm_predictor.train_and_predict(df_ml, target_col="temperature")
    df_dl, autoenc_sum = autoencoder.fit_and_evaluate(df_lstm)

    # Step 4: Integrity Validation & Consensus Scoring
    evaluated_df = validator.evaluate_dataset(df_dl, raw_df=df)
    metrics = validator.get_integrity_metrics(evaluated_df)

    # Step 5: Alerts Generation
    alerts = alert_mgr.generate_alerts_from_evaluation(evaluated_df)

    # Step 6: Save to SQLite Database
    dataset_id = save_analysis_run(filename, evaluated_df, metrics, alerts)

    # Update active state
    ACTIVE_DATA["filename"] = filename
    ACTIVE_DATA["evaluated_df"] = evaluated_df
    ACTIVE_DATA["metrics"] = metrics
    ACTIVE_DATA["iso_summary"] = iso_sum
    ACTIVE_DATA["lof_summary"] = lof_sum
    ACTIVE_DATA["zscore_summary"] = zscore_sum
    ACTIVE_DATA["lstm_summary"] = lstm_sum
    ACTIVE_DATA["autoenc_summary"] = autoenc_sum
    ACTIVE_DATA["alerts"] = alerts
    ACTIVE_DATA["dataset_id"] = dataset_id

    return evaluated_df, metrics, alerts

def get_chart_data(evaluated_df: pd.DataFrame):
    """Prepares JSON-serializable chart data for Plotly."""
    if evaluated_df is None or len(evaluated_df) == 0:
        return {
            "timestamps": [], "temperatures": [], "humidities": [],
            "wind_speeds": [], "rainfalls": [], "anomaly_indices": [],
            "iso_indices": [], "lof_indices": [], "z_indices": [],
            "lstm_preds": [], "autoencoder_losses": []
        }

    # Downsample if dataset is very large for smooth browser rendering
    df_plot = evaluated_df.head(500) if len(evaluated_df) > 500 else evaluated_df

    ts = [str(t) for t in df_plot["timestamp"]]
    temps = [float(v) if pd.notnull(v) else 0.0 for v in df_plot["temperature"]]
    hums = [float(v) if pd.notnull(v) else 0.0 for v in df_plot["humidity"]]
    winds = [float(v) if pd.notnull(v) else 0.0 for v in df_plot["wind_speed"]]
    rains = [float(v) if pd.notnull(v) else 0.0 for v in df_plot["rainfall"]]

    anom_indices = [i for i, row in df_plot.iterrows() if row.get("integrity_status") != "VERIFIED_NORMAL"]
    iso_indices = [i for i, row in df_plot.iterrows() if row.get("iso_forest_anomaly", 0) == 1]
    lof_indices = [i for i, row in df_plot.iterrows() if row.get("lof_anomaly", 0) == 1]
    z_indices = [i for i, row in df_plot.iterrows() if row.get("zscore_anomaly", 0) == 1]

    lstm_preds = [float(v) if pd.notnull(v) else None for v in df_plot.get("lstm_predicted", [])]
    ae_losses = [float(v) if pd.notnull(v) else 0.0 for v in df_plot.get("autoencoder_loss", [])]

    return {
        "timestamps": ts,
        "temperatures": temps,
        "humidities": hums,
        "wind_speeds": winds,
        "rainfalls": rains,
        "anomaly_indices": anom_indices,
        "iso_indices": iso_indices,
        "lof_indices": lof_indices,
        "z_indices": z_indices,
        "lstm_preds": lstm_preds,
        "autoencoder_losses": ae_losses
    }

# ----------------- FLASK ROUTES ----------------- #

@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    # Load default sample if no dataset in session
    if ACTIVE_DATA["evaluated_df"] is None:
        sample_path = "data/raw/weather_sample_realistic.csv"
        if not os.path.exists(sample_path):
            from data.generate_datasets import generate_synthetic_weather
            df_sample = generate_synthetic_weather(num_days=60, inject_anomalies=True)
            df_sample.to_csv(sample_path, index=False)
        df_load = pd.read_csv(sample_path)
        run_full_integrity_pipeline(df_load, "weather_sample_realistic.csv")

    chart_data = get_chart_data(ACTIVE_DATA["evaluated_df"])
    return render_template(
        "dashboard.html",
        metrics=ACTIVE_DATA["metrics"],
        iso_summary=ACTIVE_DATA["iso_summary"],
        lof_summary=ACTIVE_DATA["lof_summary"],
        zscore_summary=ACTIVE_DATA["zscore_summary"],
        autoenc_summary=ACTIVE_DATA["autoenc_summary"],
        alerts=ACTIVE_DATA["alerts"],
        current_alerts_count=len(ACTIVE_DATA["alerts"]),
        chart_data=chart_data
    )

@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    return render_template("upload.html", current_alerts_count=len(ACTIVE_DATA["alerts"]))

@app.route("/upload/process", methods=["POST"])
def upload_dataset():
    if "file" not in request.files:
        flash("No file part in upload request.", "error")
        return redirect(url_for("upload_page"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "warning")
        return redirect(url_for("upload_page"))

    if file and file.filename.endswith(".csv"):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)

        try:
            df = pd.read_csv(save_path)
            # Basic schema validation
            req_cols = ["temperature", "humidity", "wind_speed", "rainfall"]
            has_cols = any(c in df.columns for c in req_cols)
            if not has_cols:
                flash("Invalid CSV format. File must contain meteorological columns (temperature, humidity, etc.).", "danger")
                return redirect(url_for("upload_page"))

            run_full_integrity_pipeline(df, filename)
            flash(f"Successfully ingested and audited '{filename}' with {len(df)} records!", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Error analyzing CSV file: {str(e)}", "danger")
            return redirect(url_for("upload_page"))
    else:
        flash("Only valid .csv files are supported.", "danger")
        return redirect(url_for("upload_page"))

@app.route("/sample/<sample_name>")
def load_sample_data(sample_name):
    from data.generate_datasets import generate_synthetic_weather
    if sample_name == "clean":
        df = generate_synthetic_weather(num_days=30, inject_anomalies=False)
        name = "weather_clean_baseline.csv"
    elif sample_name == "demo":
        df = generate_synthetic_weather(num_days=7, inject_anomalies=True)
        name = "weather_demo_7days.csv"
    else:
        df = generate_synthetic_weather(num_days=60, inject_anomalies=True)
        name = "weather_sample_realistic.csv"

    os.makedirs("data/raw", exist_ok=True)
    df.to_csv(os.path.join("data/raw", name), index=False)
    run_full_integrity_pipeline(df, name)
    flash(f"Loaded benchmark dataset: '{name}' ({len(df)} records).", "info")
    return redirect(url_for("dashboard"))

@app.route("/visualize")
def visualize_page():
    chart_data = get_chart_data(ACTIVE_DATA["evaluated_df"])
    return render_template(
        "visualize.html",
        chart_data=chart_data,
        current_alerts_count=len(ACTIVE_DATA["alerts"])
    )

@app.route("/anomalies")
def anomalies_page():
    chart_data = get_chart_data(ACTIVE_DATA["evaluated_df"])
    df = ACTIVE_DATA["evaluated_df"]
    anomaly_rows = []
    if df is not None:
        for _, row in df.iterrows():
            flags = (row.get("iso_forest_anomaly", 0) + row.get("lof_anomaly", 0) + row.get("zscore_anomaly", 0))
            if flags > 0 or row.get("integrity_status") != "VERIFIED_NORMAL":
                anomaly_rows.append({
                    "timestamp": str(row.get("timestamp")),
                    "temperature": row.get("temperature"),
                    "humidity": row.get("humidity"),
                    "wind_speed": row.get("wind_speed"),
                    "rainfall": row.get("rainfall"),
                    "iso_forest_anomaly": row.get("iso_forest_anomaly", 0),
                    "lof_anomaly": row.get("lof_anomaly", 0),
                    "zscore_anomaly": row.get("zscore_anomaly", 0),
                    "agreement": flags
                })

    return render_template(
        "anomalies.html",
        iso_summary=ACTIVE_DATA["iso_summary"],
        lof_summary=ACTIVE_DATA["lof_summary"],
        zscore_summary=ACTIVE_DATA["zscore_summary"],
        chart_data=chart_data,
        anomaly_rows=anomaly_rows,
        current_alerts_count=len(ACTIVE_DATA["alerts"])
    )

@app.route("/predictions")
def predictions_page():
    chart_data = get_chart_data(ACTIVE_DATA["evaluated_df"])
    return render_template(
        "predictions.html",
        lstm_summary=ACTIVE_DATA["lstm_summary"],
        autoenc_summary=ACTIVE_DATA["autoenc_summary"],
        chart_data=chart_data,
        current_alerts_count=len(ACTIVE_DATA["alerts"])
    )

@app.route("/alerts")
def alerts_page():
    alert_mgr = AlertManager()
    alert_mgr.alerts = ACTIVE_DATA["alerts"]
    alert_summary = alert_mgr.get_summary()
    return render_template(
        "alerts.html",
        alerts=ACTIVE_DATA["alerts"],
        alert_summary=alert_summary,
        current_alerts_count=len(ACTIVE_DATA["alerts"])
    )

@app.route("/reports")
def reports_page():
    recent_datasets = get_recent_datasets(limit=10)
    return render_template(
        "reports.html",
        recent_datasets=recent_datasets,
        current_alerts_count=len(ACTIVE_DATA["alerts"])
    )

@app.route("/about")
def about_page():
    return render_template("about.html", current_alerts_count=len(ACTIVE_DATA["alerts"]))

@app.route("/download/cleaned")
def download_cleaned_dataset():
    df = ACTIVE_DATA["evaluated_df"]
    if df is None:
        flash("No active dataset to download.", "warning")
        return redirect(url_for("reports_page"))

    out_path = "data/processed/weather_sanitized_audit.csv"
    export_cleaned_csv(df, out_path)
    return send_file(out_path, as_attachment=True, download_name="weather_sanitized_audit.csv", mimetype="text/csv")

@app.route("/download/pdf")
def download_pdf_report():
    df = ACTIVE_DATA["evaluated_df"]
    if df is None:
        flash("No active audit report available. Please load or upload a dataset first.", "warning")
        return redirect(url_for("reports_page"))

    out_path = "reports/Weather_Integrity_Audit_Report.pdf"
    generate_pdf_report(ACTIVE_DATA["filename"], ACTIVE_DATA["metrics"], ACTIVE_DATA["alerts"], out_path)
    return send_file(out_path, as_attachment=True, download_name="Weather_Integrity_Audit_Report.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    print("Starting AI-Based Weather Data Integrity System...")
    print("Serving on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
