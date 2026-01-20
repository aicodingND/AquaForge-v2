@echo off
echo ========================================
echo AquaForge Development Server
echo ========================================
echo.

:: Start Backend API on port 8001
echo Starting FastAPI backend on port 8001...
start "AquaForge API" cmd /c ".venv\Scripts\python.exe run_server.py --mode api"

:: Wait for API to be ready
timeout /t 3 /nobreak > nul

:: Start Frontend on port 3000
echo Starting Next.js frontend on port 3000...
start "AquaForge Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo ========================================
echo Both servers starting:
echo   Backend API: http://localhost:8001
echo   Frontend:    http://localhost:3000
echo ========================================
echo.
echo Press any key to open the frontend in your browser...
pause > nul
start http://localhost:3000
