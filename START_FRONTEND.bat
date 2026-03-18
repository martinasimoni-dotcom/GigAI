@echo off
REM GigAI Frontend Dashboard Starter
REM This script starts the React/Next.js frontend server

title GigAI Frontend Dashboard (http://localhost:3000)
cls

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                   GIGAI FRONTEND DASHBOARD - STARTING                      ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo Dashboard URL:       http://localhost:3000
echo Backend Required:    http://localhost:8000
echo.
echo IMPORTANT: Backend server must be running before this starts!
echo.
echo Starting Next.js development server...
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
	echo Installing frontend dependencies...
	npm install
)

npm run dev

echo.
echo Server stopped. Press any key to close.
pause
