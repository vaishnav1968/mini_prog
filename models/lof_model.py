"""
Local Outlier Factor (LOF) Anomaly Detection Model
=================================================
Local Outlier Factor measures the local density deviation of a given data point
with respect to its k-nearest neighbors. Points that have substantially lower 
density than their neighbors are identified as outliers (local anomalies).
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor
from typing import Dict, Any, Tuple

class WeatherLOF:
    def __init__(self, n_neighbors: int = 20, contamination: float = 0.05):
        self.n_neighbors = n_neighbors
        self.contamination = contamination
        self.model = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=contamination,
            novelty=False
        )
        self.feature_cols = ["temperature", "humidity", "wind_speed", "rainfall"]

    def fit_predict(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Fits LOF and predicts local anomaly flags (-1 for anomaly, 1 for normal).
        """
        features = [col for col in self.feature_cols if col in df.columns]
        X = df[features].fillna(df[features].median())

        # Adjust neighbors if dataset is small
        n_samples = len(X)
        if n_samples <= self.n_neighbors:
            actual_neighbors = max(2, n_samples - 1)
            self.model = LocalOutlierFactor(
                n_neighbors=actual_neighbors,
                contamination=self.contamination,
                novelty=False
            )

        predictions = self.model.fit_predict(X)  # -1 = outlier, 1 = inlier
        # negative_outlier_factor_: closer to -1 means normal, large negative means outlier
        scores = self.model.negative_outlier_factor_

        res_df = df.copy()
        res_df["lof_pred"] = predictions
        res_df["lof_score"] = scores
        res_df["lof_anomaly"] = (predictions == -1).astype(int)

        return predictions, scores, res_df

    def get_summary(self, res_df: pd.DataFrame) -> Dict[str, Any]:
        total = len(res_df)
        anomalies = int(res_df["lof_anomaly"].sum())
        return {
            "algorithm": "Local Outlier Factor (LOF)",
            "total_records": total,
            "anomalies_detected": anomalies,
            "anomaly_rate_percent": round((anomalies / total) * 100, 2) if total > 0 else 0.0,
            "n_neighbors": self.n_neighbors
        }
