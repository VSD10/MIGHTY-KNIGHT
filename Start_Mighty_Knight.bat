@echo off
title Mighty Knight Academy Scheduler Launcher
echo ===================================================
echo   Starting Mighty Knight Academy Scheduling System
echo ===================================================
echo.

:: Ensure working directory is the repository root
cd /d "%~dp0"

:: Start Backend API Server
echo [1/3] Starting Backend Server on http://127.0.0.1:8000 ...
set PYTHONPATH=backend
start "Mighty Knight Backend" /b python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

:: Wait 3 seconds for backend initialization
timeout /t 3 /nobreak > nul

:: Start Frontend Server
echo [2/3] Starting Frontend UI on http://localhost:5173 ...
cd /d "%~dp0frontend"
start "Mighty Knight Frontend" /b cmd /c "npm run dev"

:: Wait 3 seconds for frontend initialization
timeout /t 3 /nobreak > nul
cd /d "%~dp0"

:: Open Browser
echo [3/3] Opening Web Application in Browser...
start http://localhost:5173/

echo.
echo ===================================================
echo   Mighty Knight is LIVE!
echo   Frontend: http://localhost:5173/
echo   Backend:  http://127.0.0.1:8000/docs
echo.
echo   Keep this window open while using the application.
echo ===================================================
pause

