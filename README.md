# AI-Based Weather Data Integrity System

An enterprise-grade, end-to-end meteorological and cybersecurity data validation platform that autonomously detects corrupted sensor readings, physical boundary violations, frozen sensors, and multi-variate anomalies using Machine Learning and Deep Learning.

---

## 🌟 Key Features

1. **Multi-Source Data Ingestion**:
   - Ingest custom weather CSV files (temperature, humidity, wind speed, rainfall).
   - Pre-loaded benchmark datasets (60-day full benchmark, 7-day quick demo, 100% clean baseline).
   - Designed for future live IoT / OpenWeather API polling.

2. **Automated Data Preprocessing**:
   - **Physical Meteorological Boundary Enforcement**: Identifies impossible temperatures (< -50°C or > 60°C), out-of-bounds humidity (< 0% or > 100%), and negative rainfall.
   - **Sensor Freeze / Persistence Detection**: Detects ADC lockup where a probe transmits zero-variance numbers for 12+ consecutive hours.
   - **Rate-of-Change Anomaly Checks**: Identifies sudden unrealistic step increases (e.g. >15°C/hr).
   - **Linear Time-Series Imputation**: Fills missing sensor values while preserving raw history.

3. **Machine Learning Anomaly Detection**:
   - **Isolation Forest**: Isolates multidimensional spikes and outliers via recursive decision tree partitioning.
   - **Local Outlier Factor (LOF)**: Detects subtle micro-climate deviations by measuring local density relative to k-nearest neighbors.
   - **Z-Score Statistical Engine**: Computes global and rolling 24-hour standard deviation distances ($|Z| > 3\sigma$).

4. **Deep Learning Integrity Modeling**:
   - **LSTM Sequence Predictor**: Recurrent neural network learning diurnal day/night cycles to predict the next hour's temperature. High prediction residuals flag temporal discrepancies.
   - **Deep Autoencoder**: Multi-layer neural network compressing weather features into a 2D bottleneck latent space. Out-of-distribution feature combinations produce high reconstruction MSE.

5. **Data Integrity & Cybersecurity Validation**:
   - Computes weighted **Integrity Scores (0 - 100)** for every observation.
   - Categorizes records: `VERIFIED_NORMAL`, `SUSPICIOUS_DRIFT`, `ANOMALOUS_READING`, `CORRUPTED_OR_TAMPERED`.
   - **Metrology vs. Cyber Clarification**: Distinguishes severe physical weather (e.g., storms with high winds and heavy rain) from corrupted/synthetic data injections.

6. **Interactive Cybersecurity Web Dashboard**:
   - High-contrast Dark Navy Theme (`#0A0F1D`) with cyan/blue accents and glassmorphism cards.
   - Real-time zoomable **Plotly.js** telemetry charts.
   - Prioritized incident alert feed (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).

7. **Audit & Report Generation**:
   - One-click export of sanitized, imputed, and anomaly-labeled CSV datasets.
   - Professional PDF audit report generation using **ReportLab** with executive summaries and recommendations.

---

## 📁 Project Directory Structure

```
weather-data-integrity/
│
├── app.py                      # Main Flask application & pipeline controller
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation & beginner guide
├── .env.example                # Sample environment configurations
│
├── data/
│   ├── generate_datasets.py    # Synthetic benchmark dataset generator
│   ├── raw/                    # Uploaded & baseline raw CSV files
│   └── processed/              # Cleaned, imputed, and audited CSV exports
│
├── preprocessing/
│   └── cleaning.py             # Preprocessing, physical checks & freeze detection
│
├── models/
│   ├── isolation_forest.py     # Isolation Forest anomaly model
│   ├── lof_model.py            # Local Outlier Factor anomaly model
│   ├── zscore_model.py         # Statistical Z-Score detector
│   ├── lstm_model.py           # LSTM time-series sequence model
│   └── autoencoder.py          # Deep Autoencoder reconstruction model
│
├── integrity/
│   └── validator.py            # Multi-model consensus validator & scoring
│
├── alerts/
│   └── alert_manager.py        # Threat & severity alert manager
│
├── database/
│   ├── db.py                   # SQLite database access layer
│   └── weather_integrity.db    # SQLite persistence file
│
├── reports/
│   └── report_generator.py     # ReportLab PDF & CSV export engine
│
├── templates/                  # Frontend HTML5 / Jinja2 Templates
│   ├── base.html               # Navigation bar, styles & layout
│   ├── dashboard.html          # Main integrity dashboard & overview
│   ├── upload.html             # CSV ingestion & preprocessing page
│   ├── visualize.html          # Synchronized meteorological telemetry
│   ├── anomalies.html          # ML model comparison & agreement table
│   ├── predictions.html        # LSTM forecast & Autoencoder loss charts
│   ├── alerts.html             # Security & sensor incident feed
│   ├── reports.html            # Downloadable audit reports & history
│   └── about.html              # Academic system architecture & methodology
│
├── static/
│   ├── css/style.css           # Dark cyber styling
│   └── js/                     # Custom JavaScript
│
└── tests/
    ├── test_pipeline.py        # Unit tests for preprocessing & ML algorithms
    └── test_server_and_routes.py # Integration tests for Flask endpoints
```

---

## 🚀 Quick Start Guide (For Beginners)

### 1. Prerequisites
Ensure you have **Python 3.10** installed on your system. Verify by opening a terminal:
```bash
python --version
```

### 2. Set Up Virtual Environment
Inside the project root directory (`mini pro`), create and activate a virtual environment:
```powershell
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# (Or Command Prompt)
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies
Install all required libraries using `pip`:
```bash
pip install -r requirements.txt
```

### 4. Generate Benchmark Datasets
Create the synthetic baseline and corrupted weather benchmark datasets:
```bash
python data/generate_datasets.py
```

### 5. Run Automated Tests
Verify that all algorithms and server routes pass:
```bash
python -m unittest discover tests
```

### 6. Start the Web Dashboard
Launch the Flask development server:
```bash
python app.py
```
Open your web browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Testing Scenarios Built Into the System

| Scenario | Input Pattern | Expected System Response | Severity |
| :--- | :--- | :--- | :--- |
| **Normal Weather** | Diurnal sine temp, realistic humidity & wind | Verified normal, 100% integrity rating | `NORMAL` |
| **Extreme Physical Spike** | Temperature $+28.5^\circ\text{C}$ in 1 hour | Flagged by Rate-of-Change, Isolation Forest, Z-Score | `CRITICAL` |
| **Negative Rainfall** | Rainfall $= -14.2\text{ mm}$ | Flagged by Physical Validator | `CRITICAL` |
| **Impossible Humidity** | Humidity $= 135\%$ | Flagged by Physical Boundary Check | `CRITICAL` |
| **Sensor ADC Lockup** | 15 consecutive identical temperature readings | Flagged by Sensor Freeze / Persistence Check | `HIGH` |
| **Subtle Density Drift** | Isolated divergence in correlated feature space | Flagged by LOF and Autoencoder Reconstruction Loss | `MEDIUM` |

---

## 🛡️ Cybersecurity & Metrological Distinction

One of the common errors in automated sensor analytics is falsely classifying severe natural storms as cyberattacks.
The **AI-Based Weather Data Integrity System** enforces a clear taxonomy:
- **Natural Storm Outliers**: Elevated wind speed matched by high precipitation, cloud cover, and drop in temperature. All parameters remain within physically possible meteorological limits.
- **Corrupted / Synthetic Injections**: Impossible thermodynamic values (e.g. freezing temperature with 100% tropical humidity, or single-minute $+30^\circ\text{C}$ steps) or hardware ADC lockups.

---

## 📄 License & Academic Attribution
Developed for Academic Internship Evaluation (2026).
Built with Python Flask, Scikit-Learn, TensorFlow/Keras, and Plotly.
