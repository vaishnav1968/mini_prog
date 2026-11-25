"""
Statistical Z-Score Anomaly Detection Model
==========================================
Computes standard deviation distance from the mean for weather parameters.
Values with |Z| > threshold (default 3.0, representing >99.7% of a normal distribution)
are classified as statistical outliers. Both Global and Rolling Window Z-scores are provided.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any

class WeatherZScoreDetector:
    def __init__(self, threshold: float = 3.0, rolling_window: int = 24):
        self.threshold = threshold
        self.rolling_window = rolling_window
        self.feature_cols = ["temperature", "humidity", "wind_speed", "rainfall"]

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes Global Z-scores and Rolling Z-scores for each meteorological variable.
        Flags any record where |Z| > threshold.
        """
        res_df = df.copy()
        anom_columns = []

        for col in self.feature_cols:
            if col in res_df.columns:
                series = res_df[col].fillna(res_df[col].median())
                std = series.std()
                mean = series.mean()

                # Global Z-Score
                if std > 1e-6:
                    z_global = (series - mean) / std
                else:
                    z_global = pd.Series(0.0, index=series.index)

                res_df[f"{col}_zscore"] = np.round(z_global, 3)
                flag_col = f"{col}_zscore_anomaly"
                res_df[flag_col] = (np.abs(z_global) > self.threshold).astype(int)
                anom_columns.append(flag_col)

                # Rolling Z-Score (tracks localized temporal anomalies)
                if len(series) >= self.rolling_window:
                    roll_mean = series.rolling(window=self.rolling_window, min_periods=3).mean()
                    roll_std = series.rolling(window=self.rolling_window, min_periods=3).std()
                    roll_z = (series - roll_mean) / (roll_std + 1e-6)
                    res_df[f"{col}_rolling_zscore"] = np.round(roll_z, 3)
                    roll_flag = f"{col}_roll_zscore_anomaly"
                    res_df[roll_flag] = (np.abs(roll_z) > self.threshold).astype(int)
                    anom_columns.append(roll_flag)

        # Combined Z-score anomaly flag (any parameter tripped)
        if anom_columns:
            res_df["zscore_anomaly"] = (res_df[anom_columns].sum(axis=1) > 0).astype(int)
        else:
            res_df["zscore_anomaly"] = 0

        return res_df

    def get_summary(self, res_df: pd.DataFrame) -> Dict[str, Any]:
        total = len(res_df)
        anomalies = int(res_df["zscore_anomaly"].sum()) if "zscore_anomaly" in res_df.columns else 0
        return {
            "algorithm": "Z-Score Statistical Outlier Detection",
            "threshold": self.threshold,
            "rolling_window": self.rolling_window,
            "total_records": total,
            "anomalies_detected": anomalies,
            "anomaly_rate_percent": round((anomalies / total) * 100, 2) if total > 0 else 0.0
        }
