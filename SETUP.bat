@echo off
REM GigAI Meeting Intelligence System - Setup Script for Windows

color 0B
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                     GigAI MEETING INTELLIGENCE v0.3.0                      ║
echo ║                    WINDOWS SETUP & VERIFICATION TOOL                       ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM 1. Check Python
echo [1] Checking Python Installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo %PYTHON_VERSION% - OK
echo.

REM 2. Check Node.js
echo [2] Checking Node.js Installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found!
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo Node.js %NODE_VERSION% - OK
echo.

REM 3. Install Python packages
echo [3] Installing Python dependencies...
pip install -q fastapi==0.104.1 uvicorn==0.24.0 pydantic==2.5.0 sqlalchemy==2.0.23 python-multipart==0.0.6 aiofiles==23.2.1
if errorlevel 1 (
    echo ERROR: Failed to install Python packages
    pause
    exit /b 1
)
echo Python packages installed - OK
echo.

REM 4. Install npm packages
echo [4] Installing npm dependencies...
cd frontend
npm install -q --legacy-peer-deps
if errorlevel 1 (
    echo ERROR: Failed to install npm packages
    cd ..
    pause
    exit /b 1
)
cd ..
echo npm packages installed - OK
echo.

REM 5. Create environment file
echo [5] Creating environment configuration...
(
    echo NEXT_PUBLIC_API_URL=http://localhost:8000
) > frontend\.env.local
echo Environment config created - OK
echo.

REM 6. Create start scripts
echo [6] Creating startup scripts...

REM Create backend starter script
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo echo ╔════════════════════════════════════════════════════════════════════════════╗
    echo echo ║                      BACKEND SERVER STARTING...                            ║
    echo echo ╚════════════════════════════════════════════════════════════════════════════╝
    echo echo.
    echo echo API Server: http://localhost:8000
    echo echo API Docs:   http://localhost:8000/docs
    echo echo.
    echo python -m uvicorn src.gigai.dashboard.dashboard_api:create_dashboard_app --reload --host 0.0.0.0 --port 8000
    echo pause
) > START_BACKEND.bat

REM Create frontend starter script
(
    echo @echo off
    echo cd /d "%%~dp0frontend"
    echo echo ╔════════════════════════════════════════════════════════════════════════════╗
    echo echo ║                      FRONTEND SERVER STARTING...                           ║
    echo echo ╚════════════════════════════════════════════════════════════════════════════╝
    echo echo.
    echo echo Dashboard: http://localhost:3000
    echo echo.
    echo npm run dev
    echo pause
) > START_FRONTEND.bat

echo Startup scripts created - OK
echo.

echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                         SETUP COMPLETE!                                    ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo SYSTEM IS READY TO USE!
echo.
echo HOW TO START:
echo ═════════════
echo.
echo 1. OPEN TERMINAL 1 (Backend):
echo    Double-click: START_BACKEND.bat
echo    Or run: python -m uvicorn src.gigai.dashboard.dashboard_api:create_dashboard_app --reload
echo.
echo 2. OPEN TERMINAL 2 (Frontend):
echo    Double-click: START_FRONTEND.bat
echo    Or run: cd frontend ^& npm run dev
echo.
echo 3. OPEN BROWSER:
echo    http://localhost:3000
echo.
echo WHAT TO EXPECT:
echo ═══════════════
echo.
echo Backend Terminal:
echo   Should show: "Application startup complete"
echo.
echo Frontend Terminal:
echo   Should show: "▲ Next.js ready in XXX ms"
echo.
echo Browser:
echo   Dashboard home page with KPI cards and data
echo.
echo URLS TO CHECK:
echo ══════════════
echo Dashboard:     http://localhost:3000
echo API Health:    http://localhost:8000/health
echo API Docs:      http://localhost:8000/docs
echo.
echo If you see "API Error" in dashboard, make sure backend is running!
echo.
pause
