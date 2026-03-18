@echo off
REM GigAI Backend Server Starter
REM This script starts the FastAPI backend server

title GigAI Backend Server (http://localhost:8000)
cls

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                     GIGAI BACKEND SERVER - STARTING                        ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo API Server URL:  http://localhost:8000
echo API Docs:        http://localhost:8000/docs
echo API Health:      http://localhost:8000/health
echo.
echo Starting FastAPI server...
echo.

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" -m uvicorn gigai.dashboard.dashboard_api:create_dashboard_app --factory --app-dir src --reload --host 127.0.0.1 --port 8000

echo.
echo Server stopped. Press any key to close.
pause
