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
echo Backend Required:    http://localhost:8010
echo.
echo IMPORTANT: Backend server must be running before this starts!
echo.
echo Starting Next.js development server...
echo.
echo Opening dashboard in your browser at http://localhost:3000 ...

cd /d "%~dp0frontend"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$tcp = New-Object System.Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 3000); exit 0 } catch { exit 1 } finally { $tcp.Dispose() }"
if %ERRORLEVEL% EQU 0 (
	echo Frontend already running on port 3000. Opening existing dashboard...
	start "" http://localhost:3000
	goto :EOF
)

if not exist "node_modules" (
	echo Installing frontend dependencies...
	npm install
)

start "" cmd /c "timeout /t 6 /nobreak >nul && start \"\" http://localhost:3000"
npm run dev

echo.
echo Server stopped. Press any key to close.
pause
