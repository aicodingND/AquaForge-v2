@echo off
REM SwimAI Docker Quick Start for Windows
REM Double-click this file to start SwimAI in development mode

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
