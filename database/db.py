"""
Database Access Layer (SQLite with MySQL Migration Ready Architecture)
======================================================================
Stores:
  - Uploaded dataset metadata
  - Weather records (raw & sanitized)
  - Anomaly detection outputs
  - Integrity evaluation logs
  - Security and meteorological alert history
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_FILE = os.environ.get("DATABASE_PATH", "database/weather_integrity.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Datasets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_records INTEGER,
        normal_records INTEGER,
        anomalous_records INTEGER,
        integrity_percentage REAL,
        status TEXT
    );
    """)

    # 2. Weather Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_id INTEGER,
        timestamp TEXT,
        temperature REAL,
        humidity REAL,
        wind_speed REAL,
        rainfall REAL,
        temperature_raw REAL,
        humidity_raw REAL,
        wind_speed_raw REAL,
        rainfall_raw REAL,
        sensor_id TEXT,
        FOREIGN KEY(dataset_id) REFERENCES datasets(id)
    );
    """)

    # 3. Integrity & Anomaly Results Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS integrity_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_id INTEGER,
        record_id INTEGER,
        timestamp TEXT,
        iso_forest_pred INTEGER,
        lof_pred INTEGER,
        zscore_flag INTEGER,
        lstm_predicted REAL,
        autoencoder_loss REAL,
        integrity_score INTEGER,
        integrity_status TEXT,
        reasons TEXT,
        FOREIGN KEY(dataset_id) REFERENCES datasets(id)
    );
    """)

    # 4. Alerts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_id INTEGER,
        timestamp TEXT,
        severity TEXT,
        parameter TEXT,
        detected_value TEXT,
        reference_range TEXT,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(dataset_id) REFERENCES datasets(id)
    );
    """)

    conn.commit()
    conn.close()

def save_analysis_run(
    filename: str,
    eval_df: pd.DataFrame,
    metrics: Dict[str, Any],
    alerts: List[Dict[str, Any]]
) -> int:
    """Saves complete dataset analysis run, records, and alerts into SQLite."""
    conn = get_connection()
    cursor = conn.cursor()

    # Insert dataset record
    cursor.execute("""
        INSERT INTO datasets (filename, total_records, normal_records, anomalous_records, integrity_percentage, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        filename,
        metrics.get("total_records", len(eval_df)),
        metrics.get("normal_readings", 0),
        metrics.get("anomalous_readings", 0) + metrics.get("corrupted_or_tampered", 0),
        metrics.get("integrity_percentage", 100.0),
        "ANALYZED"
    ))
    dataset_id = cursor.lastrowid

    # Insert batch alerts
    for a in alerts:
        cursor.execute("""
            INSERT INTO alerts (dataset_id, timestamp, severity, parameter, detected_value, reference_range, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dataset_id,
            a.get("timestamp"),
            a.get("severity"),
            a.get("parameter"),
            a.get("detected_value"),
            a.get("reference_range"),
            a.get("reason")
        ))

    conn.commit()
    conn.close()
    return dataset_id

def get_recent_datasets(limit: int = 5) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM datasets ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
