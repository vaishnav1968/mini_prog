"""
LSTM Neural Network for Weather Sequence Prediction & Residual Anomaly Detection
================================================================================
Long Short-Term Memory (LSTM) recurrent networks capture temporal dependencies
and diurnal/seasonal patterns in weather time series.

Integrity Detection Principle:
  1. Train sequence model on historical time-series sequences (e.g. 24-hour lookback).
  2. Model predicts the next hour's temperature.
  3. Residual = |Actual - Predicted|.
  4. If the residual exceeds dynamic error bounds, the reading is flagged as a temporal anomaly.
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.preprocessing import MinMaxScaler

class WeatherLSTMPredictor:
    def __init__(self, sequence_length: int = 24, epochs: int = 10, batch_size: int = 32):
        self.sequence_length = sequence_length
        self.epochs = epochs
        self.batch_size = batch_size
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None

    def prepare_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Converts 1D time-series into sliding window sequences: (X[t-seq_len...t-1] -> y[t])"""
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:i + self.sequence_length])
            y.append(data[i + self.sequence_length])
        return np.array(X), np.array(y)

    def train_and_predict(
        self,
        df: pd.DataFrame,
        target_col: str = "temperature",
        threshold_multiplier: float = 3.0
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Trains sequence model on time series data, generates predictions and detects residual anomalies.
        Uses TensorFlow/Keras LSTM if available; provides an MLP sliding-window sequential model fallback.
        """
        series = df[target_col].ffill().bfill().values.reshape(-1, 1)

        # Fallback if dataset is too small for sequences
        if len(series) <= self.sequence_length + 5:
            res_df = df.copy()
            res_df["lstm_predicted"] = res_df[target_col]
            res_df["lstm_residual"] = 0.0
            res_df["lstm_anomaly"] = 0
            return res_df, {
                "status": "insufficient_data",
                "model": "Sequential Predictor (Data Limited)",
                "message": f"Requires at least {self.sequence_length + 5} records for sequence modeling. Fallback applied.",
                "anomalies_detected": 0,
                "residual_threshold": 3.0,
                "final_mae": 0.0
            }

        scaled_data = self.scaler.fit_transform(series)
        X, y = self.prepare_sequences(scaled_data)

        has_tf = False
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from tensorflow.keras.optimizers import Adam
            has_tf = True
        except ImportError:
            has_tf = False

        if has_tf:
            # Build TensorFlow Keras LSTM
            self.model = Sequential([
                LSTM(32, activation="tanh", return_sequences=True, input_shape=(self.sequence_length, 1)),
                Dropout(0.1),
                LSTM(16, activation="tanh"),
                Dense(8, activation="relu"),
                Dense(1)
            ])
            self.model.compile(optimizer=Adam(learning_rate=0.005), loss="mse", metrics=["mae"])
            history = self.model.fit(
                X, y,
                epochs=min(self.epochs, 8),
                batch_size=self.batch_size,
                verbose=0,
                shuffle=False
            )
            predicted_scaled = self.model.predict(X, verbose=0)
            model_type = "LSTM Recurrent Neural Network (TensorFlow/Keras)"
            final_mae = float(history.history["mae"][-1]) if "mae" in history.history else 0.5
        else:
            # Resilient Scikit-learn MLP Sequential Neural Regressor Fallback
            from sklearn.neural_network import MLPRegressor
            X_flat = X.reshape(X.shape[0], -1)
            self.model = MLPRegressor(
                hidden_layer_sizes=(32, 16),
                activation="relu",
                max_iter=min(self.epochs * 15, 80),
                random_state=42
            )
            self.model.fit(X_flat, y.ravel())
            predicted_scaled = self.model.predict(X_flat).reshape(-1, 1)
            model_type = "Sequential Neural Predictor (MLP Recurrent Equivalent)"
            final_mae = float(np.mean(np.abs(y.ravel() - predicted_scaled.ravel())))

        predicted_values = self.scaler.inverse_transform(predicted_scaled).flatten()

        # Build results aligned with original dataframe
        res_df = df.copy()
        padding = [np.nan] * self.sequence_length
        full_preds = padding + list(predicted_values)
        res_df["lstm_predicted"] = full_preds

        actuals = res_df[target_col].values
        residuals = np.abs(actuals - np.array(full_preds))
        res_df["lstm_residual"] = residuals

        # Dynamic threshold
        valid_residuals = residuals[~np.isnan(residuals)]
        mean_res = np.mean(valid_residuals) if len(valid_residuals) > 0 else 0.0
        std_res = np.std(valid_residuals) if len(valid_residuals) > 0 else 1.0
        threshold = mean_res + (threshold_multiplier * std_res)

        res_df["lstm_anomaly"] = (res_df["lstm_residual"] > threshold).astype(int)

        summary = {
            "model": model_type,
            "sequence_window_hours": self.sequence_length,
            "final_mae": round(final_mae, 4),
            "residual_mean": round(float(mean_res), 3),
            "residual_threshold": round(float(threshold), 3),
            "anomalies_detected": int(res_df["lstm_anomaly"].sum())
        }

        return res_df, summary
