"""
Weather Dataset Generator for AI Data Integrity Testing
--------------------------------------------------------
Generates realistic hourly weather data with intentional anomalies,
including:
  1. Temperature spikes (sensor glitch or injection attack)
  2. Frozen/stuck sensor readings (sensor hardware failure)
  3. Negative rainfall or impossible humidity (>100% or <0%)
  4. Missing values (communication packet drops)
  5. Sudden unrealistic weather jumps (incompatible temp/humidity jumps)
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_weather(
    num_days=60,
    start_date="2026-01-01 00:00:00",
    inject_anomalies=True,
    random_seed=42
):
    np.random.seed(random_seed)
    total_hours = num_days * 24
    
    start_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    timestamps = [start_dt + timedelta(hours=i) for i in range(total_hours)]
    
    hours = np.array([ts.hour for ts in timestamps])
    day_of_year = np.array([ts.timetuple().tm_yday for ts in timestamps])
    
    # 1. Base Diurnal (Day/Night) and Seasonal Temperature Cycle
    # Peak at 14:00 (2 PM), low at 05:00 (5 AM)
    daily_temp_cycle = 7.0 * np.sin((hours - 8) * (2 * np.pi / 24))
    seasonal_temp = 22.0 + 5.0 * np.sin(day_of_year * (2 * np.pi / 365))
    noise_temp = np.random.normal(0, 1.2, total_hours)
    temperature = seasonal_temp + daily_temp_cycle + noise_temp
    
    # 2. Relative Humidity (inversely correlated with temperature)
    base_humidity = 65.0 - (daily_temp_cycle * 2.5) + np.random.normal(0, 4.0, total_hours)
    humidity = np.clip(base_humidity, 20.0, 95.0)
    
    # 3. Wind Speed (Weibull/Rayleigh-like distribution)
    base_wind = np.random.weibull(1.8, total_hours) * 12.0
    wind_speed = np.clip(base_wind, 0.5, 45.0)
    
    # 4. Rainfall (mostly 0, with occasional rainy periods)
    rainfall = np.zeros(total_hours)
    rain_events = np.random.choice([0, 1], size=total_hours, p=[0.93, 0.07])
    for i in range(total_hours):
        if rain_events[i] == 1:
            rain_duration = np.random.randint(2, 6)
            intensity = np.random.exponential(4.5)
            for d in range(min(rain_duration, total_hours - i)):
                rainfall[i + d] += round(float(np.random.uniform(0.5, intensity)), 1)
                humidity[i + d] = min(98.0, humidity[i + d] + 15.0)
    
    df = pd.DataFrame({
        "timestamp": [ts.strftime("%Y-%m-%d %H:%M:%S") for ts in timestamps],
        "temperature": np.round(temperature, 1),
        "humidity": np.round(humidity, 1),
        "wind_speed": np.round(wind_speed, 1),
        "rainfall": np.round(rainfall, 1),
        "sensor_id": "STATION_ALPHA_01"
    })
    
    if not inject_anomalies:
        return df
    
    # Intentionally inject specific realistic integrity anomalies for testing
    n = len(df)
    # A. Temperature Spikes (+25C sudden jump - sensor glitch / heating wire)
    spike_indices = [int(n * 0.12), int(n * 0.45), int(n * 0.78)]
    for idx in spike_indices:
        if idx < n:
            df.loc[idx, "temperature"] += 28.5
            
    # B. Impossible Negative Rainfall
    neg_rain_indices = [int(n * 0.22), int(n * 0.65)]
    for idx in neg_rain_indices:
        if idx < n:
            df.loc[idx, "rainfall"] = -14.2
            
    # C. Out-of-bounds Humidity (>100% or <0%)
    invalid_hum_indices = [int(n * 0.31), int(n * 0.88)]
    for idx in invalid_hum_indices:
        if idx < n:
            df.loc[idx, "humidity"] = 135.0
            
    # D. Stuck / Frozen Sensor (Zero variance for 15 hours)
    freeze_start = int(n * 0.38)
    if freeze_start < n:
        frozen_val = df.loc[freeze_start, "temperature"]
        for i in range(freeze_start, min(freeze_start + 18, n)):
            df.loc[i, "temperature"] = frozen_val
        
    # E. Extreme Wind Gust (hurricane anomaly or sensor fault)
    wind_spike_idx = [int(n * 0.55)]
    for idx in wind_spike_idx:
        if idx < n:
            df.loc[idx, "wind_speed"] = 165.0
            
    # F. Missing Values (Communication dropouts / packet loss)
    missing_indices = [int(n * 0.18), int(n * 0.19), int(n * 0.72)]
    for idx in missing_indices:
        if idx < n:
            col_target = np.random.choice(["temperature", "humidity", "wind_speed"])
            df.loc[idx, col_target] = np.nan
            
    return df

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    
    # 1. Baseline Clean Dataset (60 days)
    df_clean = generate_synthetic_weather(num_days=60, inject_anomalies=False)
    clean_path = "data/raw/weather_clean_baseline.csv"
    df_clean.to_csv(clean_path, index=False)
    print(f"Generated clean baseline dataset: {clean_path} ({len(df_clean)} rows)")
    
    # 2. Benchmark Evaluation Dataset with known anomalies (60 days = 1440 hourly records)
    df_corrupted = generate_synthetic_weather(num_days=60, inject_anomalies=True)
    test_path = "data/raw/weather_sample_realistic.csv"
    df_corrupted.to_csv(test_path, index=False)
    print(f"Generated realistic test dataset with anomalies: {test_path} ({len(df_corrupted)} rows)")
    
    # 3. Quick Demo Dataset (7 days = 168 hours) for fast interactive testing
    df_demo = generate_synthetic_weather(num_days=7, inject_anomalies=True)
    demo_path = "data/raw/weather_demo_7days.csv"
    df_demo.to_csv(demo_path, index=False)
    print(f"Generated demo 7-day dataset: {demo_path} ({len(df_demo)} rows)")
