@echo off
REM ============================================
REM DEPRECATED (2026-02-11)
REM macOS is the canonical platform.
REM Use: docker-compose --profile dev up --build
REM This file will be removed in a future cleanup.
REM ============================================
REM SwimAI Docker Quick Start (Legacy Windows)

echo.
echo ================================================
echo    SwimAI - Starting in Development Mode
echo ================================================
echo.

cd /d "%~dp0"

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting SwimAI...
echo.
echo Frontend will be available at: http://localhost:3000
echo Backend API will be available at: http://localhost:8000
echo.
echo Press Ctrl+C to stop
echo.

docker-compose --profile dev up --build

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start SwimAI
    pause
    exit /b 1
)

pause
