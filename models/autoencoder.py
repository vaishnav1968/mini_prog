"""
Deep Autoencoder Model for Multi-Variate Anomaly Detection
==========================================================
An Autoencoder neural network compresses multi-variate weather records (temperature,
humidity, wind speed, rainfall) into a low-dimensional bottleneck latent representation,
then reconstructs the original features.

Integrity Detection Principle:
  1. The network is trained to reconstruct normal correlated weather patterns.
  2. Corrupted data, impossible multi-parameter combinations, or manipulated readings
     cannot be accurately reconstructed.
  3. High Reconstruction Mean Squared Error (MSE) > threshold flags the record as anomalous.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.preprocessing import StandardScaler

class WeatherAutoencoder:
    def __init__(self, latent_dim: int = 2, epochs: int = 15, batch_size: int = 32):
        self.latent_dim = latent_dim
        self.epochs = epochs
        self.batch_size = batch_size
        self.scaler = StandardScaler()
        self.model = None
        self.feature_cols = ["temperature", "humidity", "wind_speed", "rainfall"]

    def fit_and_evaluate(
        self,
        df: pd.DataFrame,
        threshold_percentile: float = 95.0
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Trains Autoencoder and flags records exceeding the reconstruction error threshold.
        Uses TensorFlow/Keras Autoencoder if available; provides Scikit-learn MLP Autoencoder.
        """
        features = [col for col in self.feature_cols if col in df.columns]
        X_raw = df[features].fillna(df[features].median()).values

        if len(X_raw) < 15:
            res_df = df.copy()
            res_df["autoencoder_loss"] = 0.0
            res_df["autoencoder_anomaly"] = 0
            return res_df, {
                "status": "insufficient_data",
                "message": "Autoencoder requires at least 15 records for feature compression.",
                "anomalies_detected": 0,
                "reconstruction_threshold": 0.1
            }

        X_scaled = self.scaler.fit_transform(X_raw)

        has_tf = False
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Model
            from tensorflow.keras.layers import Input, Dense
            from tensorflow.keras.optimizers import Adam
            has_tf = True
        except ImportError:
            has_tf = False

        if has_tf:
            input_dim = len(features)
            inputs = Input(shape=(input_dim,))
            encoded = Dense(8, activation="relu")(inputs)
            encoded = Dense(self.latent_dim, activation="relu")(encoded)
            decoded = Dense(8, activation="relu")(encoded)
            outputs = Dense(input_dim, activation="linear")(decoded)

            self.model = Model(inputs=inputs, outputs=outputs)
            self.model.compile(optimizer=Adam(learning_rate=0.005), loss="mse")
            self.model.fit(
                X_scaled, X_scaled,
                epochs=min(self.epochs, 12),
                batch_size=self.batch_size,
                verbose=0,
                shuffle=True
            )
            X_reconstructed = self.model.predict(X_scaled, verbose=0)
            model_name = "Deep Autoencoder (TensorFlow/Keras)"
        else:
            # Scikit-learn MLP Autoencoder Neural Network (Input -> 8 -> 2 -> 8 -> Output)
            from sklearn.neural_network import MLPRegressor
            self.model = MLPRegressor(
                hidden_layer_sizes=(8, self.latent_dim, 8),
                activation="relu",
                max_iter=min(self.epochs * 15, 80),
                random_state=42
            )
            self.model.fit(X_scaled, X_scaled)
            X_reconstructed = self.model.predict(X_scaled)
            model_name = "Deep Neural Autoencoder (MLP Bottleneck)"

        # Compute reconstruction error per sample (MSE across all features)
        reconstruction_errors = np.mean(np.square(X_scaled - X_reconstructed), axis=1)

        # Threshold based on 95th percentile
        threshold = float(np.percentile(reconstruction_errors, threshold_percentile))

        res_df = df.copy()
        res_df["autoencoder_loss"] = reconstruction_errors.round(4)
        res_df["autoencoder_anomaly"] = (reconstruction_errors > threshold).astype(int)

        summary = {
            "model": model_name,
            "latent_bottleneck_dim": self.latent_dim,
            "reconstruction_threshold": round(threshold, 4),
            "anomalies_detected": int(res_df["autoencoder_anomaly"].sum())
        }

        return res_df, summary
