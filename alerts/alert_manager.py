"""
Alert Management and Threat Intelligence Engine
===============================================
Generates structured security & meteorological alerts:
  - LOW: Minor statistical variation or single mild ML indicator.
  - MEDIUM: Suspicious drift, multiple mild indicators.
  - HIGH: Multi-model confirmed anomalous reading or significant prediction residual.
  - CRITICAL: Physical impossibility, negative rainfall, sensor freeze, extreme spike (tampering/hardware fault).
"""

from datetime import datetime
from typing import List, Dict, Any
import pandas as pd

class AlertManager:
    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []

    def generate_alerts_from_evaluation(self, eval_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Scans evaluated dataframe and populates structured alerts.
        """
        alerts = []
        for idx, row in eval_df.iterrows():
            status = row.get("integrity_status", "VERIFIED_NORMAL")
            if status == "VERIFIED_NORMAL":
                continue

            score = row.get("integrity_score", 100)
            reasons = row.get("reasons", "")
            ts = str(row.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))

            # Determine severity
            if status == "CORRUPTED_OR_TAMPERED" or score <= 40:
                severity = "CRITICAL"
            elif status == "ANOMALOUS_READING" or score <= 60:
                severity = "HIGH"
            elif status == "SUSPICIOUS_DRIFT" or score <= 80:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            # Determine primary parameter involved
            param = "Multi-Parameter"
            val_str = "N/A"
            ref_range = "Standard Meteorologic"

            if "temperature" in reasons.lower():
                param = "Temperature"
                raw_val = row.get("temperature_raw", row.get("temperature", "N/A"))
                val_str = f"{raw_val}°C"
                ref_range = "-50°C to +60°C"
            elif "humidity" in reasons.lower():
                param = "Humidity"
                raw_val = row.get("humidity_raw", row.get("humidity", "N/A"))
                val_str = f"{raw_val}%"
                ref_range = "0% to 100%"
            elif "rainfall" in reasons.lower():
                param = "Rainfall"
                raw_val = row.get("rainfall_raw", row.get("rainfall", "N/A"))
                val_str = f"{raw_val} mm"
                ref_range = ">= 0.0 mm"
            elif "wind" in reasons.lower():
                param = "Wind Speed"
                val_str = f"{row.get('wind_speed', 'N/A')} km/h"
                ref_range = "0 to 120 km/h"

            alert_item = {
                "id": len(alerts) + 1,
                "timestamp": ts,
                "severity": severity,
                "parameter": param,
                "detected_value": val_str,
                "reference_range": ref_range,
                "reason": reasons,
                "integrity_score": score,
                "status": status
            }
            alerts.append(alert_item)

        self.alerts = alerts
        return alerts

    def get_summary(self) -> Dict[str, Any]:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for a in self.alerts:
            sev = a.get("severity", "LOW")
            counts[sev] = counts.get(sev, 0) + 1
        return {
            "total_alerts": len(self.alerts),
            "severity_counts": counts,
            "requires_immediate_action": counts["CRITICAL"] + counts["HIGH"]
        }
