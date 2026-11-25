"""
Isolation Forest Anomaly Detection Model
========================================
Isolation Forest explicitly isolates anomalies instead of profiling normal points.
Because anomalies are few and have distinct attribute values, they are isolated 
closer to the root of randomized decision trees (shorter average path length).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import Dict, Any, Tuple

class WeatherIsolationForest:
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=150,
            max_samples="auto"
        )
        self.feature_cols = ["temperature", "humidity", "wind_speed", "rainfall"]

    def fit_predict(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Fits Isolation Forest and predicts anomaly flags (-1 for anomaly, 1 for normal).
        Returns:
          - predictions: 1 (normal), -1 (anomaly)
          - anomaly_scores: continuous anomaly scores (lower = more abnormal)
          - annotated_df: DataFrame with model results added
        """
        features = [col for col in self.feature_cols if col in df.columns]
        X = df[features].fillna(df[features].median())

        self.model.fit(X)
        predictions = self.model.predict(X)  # -1 for anomaly, 1 for normal
        scores = self.model.decision_function(X)  # lower = more abnormal

        res_df = df.copy()
        res_df["iso_forest_pred"] = predictions
        res_df["iso_forest_score"] = scores
        # 1 means anomaly detected, 0 normal
        res_df["iso_forest_anomaly"] = (predictions == -1).astype(int)

        return predictions, scores, res_df

    def get_summary(self, res_df: pd.DataFrame) -> Dict[str, Any]:
        total = len(res_df)
        anomalies = int(res_df["iso_forest_anomaly"].sum())
        return {
            "algorithm": "Isolation Forest",
            "total_records": total,
            "anomalies_detected": anomalies,
            "anomaly_rate_percent": round((anomalies / total) * 100, 2) if total > 0 else 0.0,
            "contamination_parameter": self.contamination
        }
