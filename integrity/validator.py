"""
Data Integrity Validation Engine
================================
Consolidates all statistical, rule-based, ML, and DL flags into a single,
defensible Data Integrity Assessment for each meteorological reading.

Cybersecurity & Metrology Principle:
  - A physical storm can cause extreme values (high wind, intense rain), which is a
    'METEOROLOGICAL_ANOMALY', NOT a cyberattack.
  - An impossible jump (+30°C in 5 min, negative rain, humidity 140%, or zero variance for 24h)
    points toward 'DATA_CORRUPTION' (sensor failure or synthetic tampering).
  - The system NEVER asserts definitive criminal hacking without cryptographic or network proof;
    it strictly reports 'POTENTIAL_TAMPERING_OR_CORRUPTION'.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List

class DataIntegrityValidator:
    def __init__(self):
        pass

    def evaluate_dataset(
        self,
        cleaned_df: pd.DataFrame,
        raw_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Combines rule-based physical flags, ML anomaly outputs, and DL outputs
        to assign an overall Integrity Score (0 - 100) and Classification Status.
        """
        eval_df = cleaned_df.copy()

        # Initialize tracking columns
        eval_df["integrity_score"] = 100
        eval_df["integrity_status"] = "VERIFIED_NORMAL"
        eval_df["reasons"] = ""

        # Weight penalty deductions
        # Physical impossibility is the most severe (-40)
        # Stuck sensor / frozen sensor (-30)
        # Rate-of-change impossible spike (-25)
        # Deep Learning sequence / autoencoder error (-15)
        # ML Outlier flag (Isolation Forest, LOF, Z-Score) (-10)

        for idx, row in eval_df.iterrows():
            penalties = 0
            reason_list = []

            # 1. Physical violations check
            for col in ["temperature", "humidity", "wind_speed", "rainfall"]:
                raw_col = f"{col}_raw"
                if raw_col in eval_df.columns:
                    val = row[raw_col]
                    if pd.notnull(val):
                        if col == "rainfall" and val < 0:
                            penalties += 40
                            reason_list.append(f"Physical limit: Negative rainfall ({val} mm)")
                        elif col == "humidity" and (val < 0 or val > 100):
                            penalties += 40
                            reason_list.append(f"Physical limit: Out-of-bounds humidity ({val}%)")
                        elif col == "temperature" and (val < -50 or val > 60):
                            penalties += 40
                            reason_list.append(f"Physical limit: Extreme temperature ({val}°C)")
                    else:
                        penalties += 15
                        reason_list.append(f"Missing reading in {col}")

            # 2. Frozen sensor check
            for col in ["temperature", "humidity"]:
                if f"{col}_is_frozen" in eval_df.columns and row[f"{col}_is_frozen"]:
                    penalties += 30
                    reason_list.append(f"Sensor Persistence: Stuck {col} reading for >=12h")

            # 3. Rate-of-change (Sudden Spikes)
            for col in ["temperature", "humidity", "wind_speed"]:
                if f"{col}_rate_violation" in eval_df.columns and row[f"{col}_rate_violation"]:
                    penalties += 25
                    delta = row.get(f"{col}_delta", 0)
                    reason_list.append(f"Unrealistic spike: {col} jumped {round(delta, 1)} in 1hr")

            # 4. Statistical & ML Anomaly flags
            ml_flags = 0
            if row.get("iso_forest_anomaly", 0) == 1:
                ml_flags += 1
            if row.get("lof_anomaly", 0) == 1:
                ml_flags += 1
            if row.get("zscore_anomaly", 0) == 1:
                ml_flags += 1

            if ml_flags >= 2:
                penalties += 20
                reason_list.append(f"Multi-model ML agreement: {ml_flags} models flagged outlier")
            elif ml_flags == 1:
                penalties += 10
                reason_list.append("Single ML model flagged outlier")

            # 5. Deep Learning flags (LSTM residual & Autoencoder)
            dl_flags = 0
            if row.get("lstm_anomaly", 0) == 1:
                dl_flags += 1
                reason_list.append("LSTM temporal sequence prediction discrepancy")
            if row.get("autoencoder_anomaly", 0) == 1:
                dl_flags += 1
                reason_list.append("Autoencoder feature reconstruction error exceeded threshold")
            penalties += (dl_flags * 15)

            # Calculate final integrity score
            final_score = max(0, 100 - penalties)
            eval_df.at[idx, "integrity_score"] = final_score
            eval_df.at[idx, "reasons"] = "; ".join(reason_list) if reason_list else "All checks passed"

            # Determine Status
            # Clear distinction: Physical impossibility or freeze -> POTENTIAL_TAMPERING_OR_CORRUPTION
            # High ML outlier with physical plausibility -> METEOROLOGICAL_ANOMALY
            if penalties >= 40 or any("Physical limit" in r or "Sensor Persistence" in r or "Unrealistic spike" in r for r in reason_list):
                eval_df.at[idx, "integrity_status"] = "CORRUPTED_OR_TAMPERED"
            elif final_score < 70:
                eval_df.at[idx, "integrity_status"] = "ANOMALOUS_READING"
            elif final_score < 85:
                eval_df.at[idx, "integrity_status"] = "SUSPICIOUS_DRIFT"
            else:
                eval_df.at[idx, "integrity_status"] = "VERIFIED_NORMAL"

        return eval_df

    def get_integrity_metrics(self, evaluated_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates global integrity statistics for the dashboard."""
        total = len(evaluated_df)
        if total == 0:
            return {}

        status_counts = evaluated_df["integrity_status"].value_counts().to_dict()
        avg_score = float(evaluated_df["integrity_score"].mean())

        normal_count = status_counts.get("VERIFIED_NORMAL", 0)
        suspicious_count = status_counts.get("SUSPICIOUS_DRIFT", 0)
        anomalous_count = status_counts.get("ANOMALOUS_READING", 0)
        corrupted_count = status_counts.get("CORRUPTED_OR_TAMPERED", 0)

        # Integrity percentage: proportion of verified normal + suspicious (un-corrupted)
        integrity_pct = round(((normal_count + (suspicious_count * 0.5)) / total) * 100, 2)

        return {
            "total_records": total,
            "average_integrity_score": round(avg_score, 1),
            "integrity_percentage": integrity_pct,
            "normal_readings": normal_count,
            "suspicious_readings": suspicious_count,
            "anomalous_readings": anomalous_count,
            "corrupted_or_tampered": corrupted_count,
            "status_breakdown": status_counts
        }
