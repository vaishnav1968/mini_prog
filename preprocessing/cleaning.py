"""
Data Preprocessing and Validation Layer
======================================
Identifies:
  - Missing values (NaN / nulls)
  - Duplicate timestamps
  - Physical boundary violations (e.g., negative rain, humidity > 100%)
  - Rate-of-change / sudden unrealistic spikes (e.g., delta > 12°C/hr)
  - Sensor freeze / persistence (stuck values over time)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

# Physical validity boundaries based on standard meteorological limits
PHYSICAL_LIMITS = {
    "temperature": (-50.0, 60.0),   # Celsius
    "humidity": (0.0, 100.0),        # Percentage
    "wind_speed": (0.0, 120.0),      # m/s or km/h (tropical cyclones max ~100m/s)
    "rainfall": (0.0, 300.0)         # mm/hr
}

# Maximum plausible 1-hour change under non-tornadic conditions
MAX_HOURLY_DELTA = {
    "temperature": 15.0,  # Max realistic temperature shift in 1 hr
    "humidity": 45.0,     # Max realistic humidity shift in 1 hr
    "wind_speed": 40.0,   # Max realistic wind speed shift in 1 hr
    "rainfall": 150.0
}

class WeatherDataPreprocessor:
    def __init__(self, physical_limits: Dict = None, max_deltas: Dict = None):
        self.physical_limits = physical_limits or PHYSICAL_LIMITS
        self.max_deltas = max_deltas or MAX_HOURLY_DELTA

    def inspect_raw_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Performs initial integrity scan of the raw dataset."""
        report = {
            "total_records": len(df),
            "columns": list(df.columns),
            "missing_counts": df.isnull().sum().to_dict(),
            "duplicate_timestamps": int(df.duplicated(subset=["timestamp"]).sum()) if "timestamp" in df.columns else 0,
            "physical_violations": {},
            "summary_stats": {}
        }

        # Check physical boundary violations
        for col, (low, high) in self.physical_limits.items():
            if col in df.columns:
                invalid_low = (df[col] < low).sum()
                invalid_high = (df[col] > high).sum()
                report["physical_violations"][col] = {
                    "below_min": int(invalid_low),
                    "above_max": int(invalid_high),
                    "total_invalid": int(invalid_low + invalid_high)
                }

        # Numeric summary
        num_cols = [c for c in ["temperature", "humidity", "wind_speed", "rainfall"] if c in df.columns]
        if num_cols:
            report["summary_stats"] = df[num_cols].describe().round(2).to_dict()

        return report

    def clean_and_impute(
        self,
        df: pd.DataFrame,
        impute_strategy: str = "interpolate"
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Cleans dataset by:
        1. Parsing timestamps and sorting
        2. Removing exact duplicate timestamps
        3. Identifying and flagging physical boundary violations
        4. Imputing missing/invalid values with interpolation or forward-fill
        5. Computing rate-of-change deltas
        """
        cleaned = df.copy()
        cleaning_log = {
            "duplicates_removed": 0,
            "interpolated_values": {},
            "frozen_sensor_periods": 0
        }

        # 1. Parse timestamps
        if "timestamp" in cleaned.columns:
            cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce")
            # Drop duplicates
            orig_len = len(cleaned)
            cleaned = cleaned.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
            cleaning_log["duplicates_removed"] = orig_len - len(cleaned)

        # 2. Flag and sanitize physical violations (set to NaN for interpolation)
        for col, (low, high) in self.physical_limits.items():
            if col in cleaned.columns:
                cleaned[f"{col}_raw"] = cleaned[col]  # Preserve original
                mask_invalid = (cleaned[col] < low) | (cleaned[col] > high)
                cleaned.loc[mask_invalid, col] = np.nan

        # 3. Handle missing values
        num_cols = [c for c in ["temperature", "humidity", "wind_speed", "rainfall"] if c in cleaned.columns]
        for col in num_cols:
            missing_count = int(cleaned[col].isnull().sum())
            cleaning_log["interpolated_values"][col] = missing_count
            if missing_count > 0:
                if impute_strategy == "interpolate":
                    # Time-series linear interpolation with forward/backward fill fallback
                    cleaned[col] = cleaned[col].interpolate(method="linear").bfill().ffill()
                elif impute_strategy == "median":
                    cleaned[col] = cleaned[col].fillna(cleaned[col].median())
                else:
                    cleaned[col] = cleaned[col].ffill().bfill()

        # 4. Detect Sensor Freeze (variance == 0 over a rolling 12-hour window)
        for col in ["temperature", "humidity"]:
            if col in cleaned.columns and len(cleaned) >= 12:
                rolling_std = cleaned[col].rolling(window=12, min_periods=12).std()
                frozen_mask = (rolling_std == 0.0)
                cleaned[f"{col}_is_frozen"] = frozen_mask.fillna(False)
                cleaning_log["frozen_sensor_periods"] += int(frozen_mask.sum())

        # 5. Compute Rate-of-Change Deltas (Spike Detection)
        for col, max_delta in self.max_deltas.items():
            if col in cleaned.columns:
                cleaned[f"{col}_delta"] = cleaned[col].diff().abs().fillna(0.0)
                cleaned[f"{col}_rate_violation"] = cleaned[f"{col}_delta"] > max_delta

        return cleaned, cleaning_log
