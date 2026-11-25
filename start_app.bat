@echo off
title AI Weather Data Integrity System
echo ====================================================
echo Starting AI-Based Weather Data Integrity System...
echo ====================================================
echo Opening web dashboard in your default browser...
start "" "http://127.0.0.1:5000"
echo Starting Flask web server...
.\venv\Scripts\python.exe app.py
pause
