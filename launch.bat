@echo off
REM ============================================
REM DEPRECATED (2026-02-11)
REM macOS is the canonical platform.
REM Use: python run_server.py --mode api --port 8001
REM This file will be removed in a future cleanup.
REM ============================================
REM AquaForge Server Launcher (Legacy Windows)
REM ============================================

echo.
echo  ========================================
echo     AquaForge Server Launcher
echo  ========================================
echo.

REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [!] No .venv found, using system Python
)

echo.
echo Select server mode:
echo   1. Reflex Only (current production mode)
echo   2. FastAPI Only (API development/testing)
echo   3. Hybrid Mode (both Reflex + FastAPI)
echo   4. FastAPI with Hot Reload (development)
echo.

set /p MODE="Enter choice (1-4): "

if "%MODE%"=="1" (
    echo.
    echo Starting Reflex...
    python run_server.py --mode reflex
) else if "%MODE%"=="2" (
    echo.
    echo Starting FastAPI on port 8001...
    python run_server.py --mode api --port 8001
) else if "%MODE%"=="3" (
    echo.
    echo Starting Hybrid Mode...
    echo   Reflex: http://localhost:3000
    echo   FastAPI: http://localhost:8001
    python run_server.py --mode hybrid
) else if "%MODE%"=="4" (
    echo.
    echo Starting FastAPI with hot reload...
    python run_server.py --mode api --port 8001 --reload
) else (
    echo Invalid choice. Starting Reflex by default...
    python run_server.py --mode reflex
)

pause
