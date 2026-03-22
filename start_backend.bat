@echo off
echo ============================================
echo  GIGAI Backend Startup
echo ============================================

echo [1/3] Killing any process on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 "') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F 2>nul
)
timeout /t 2 /nobreak >nul

echo [2/3] Activating virtual environment...
call "%~dp0.venv\Scripts\activate.bat"

echo [3/3] Starting backend on port 8000 (no reload)...
echo ============================================
cd /d "%~dp0backend"
python -u main.py
