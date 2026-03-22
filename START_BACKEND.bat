@echo off
REM GigAI Backend Server Starter
REM This script starts both dashboard and orchestrator APIs

title GigAI Backend Services
cls

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                     GIGAI BACKEND SERVER - STARTING                        ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo Dashboard API:    http://localhost:8010
echo Dashboard Docs:   http://localhost:8010/docs
echo Orchestrator API: http://localhost:8011
echo Orchestrator Docs:http://localhost:8011/docs
echo.
echo Starting backend services...
echo.

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" ".\RUN_GIGAI.py" --mode backend --reload --stop-existing

echo.
echo Server stopped. Press any key to close.
pause
