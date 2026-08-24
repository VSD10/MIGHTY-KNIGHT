@echo off
title Mighty Knight Academy Scheduler Launcher
echo ===================================================
echo   Starting Mighty Knight Academy Scheduling System
echo ===================================================
echo.

:: Start Backend API Server
echo Starting Backend Server on http://127.0.0.1:8000 ...
set PYTHONPATH=backend
start /b python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > nul 2>&1

:: Wait 2 seconds
timeout /t 2 /nobreak > nul

:: Start Frontend Server
echo Starting Web UI on http://localhost:5173 ...
cd frontend
start /b npm run dev > nul 2>&1

:: Wait 2 seconds
timeout /t 2 /nobreak > nul

:: Open Browser
echo Opening Web Application in Browser...
start http://localhost:5173/

echo.
echo ===================================================
echo   Mighty Knight is LIVE at http://localhost:5173/
echo   Keep this window open while using the app.
echo ===================================================
pause
