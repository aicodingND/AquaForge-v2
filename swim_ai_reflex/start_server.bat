@echo off
:: AquaForge Server Restart Script
:: Kills any stale processes, clears cache, and starts fresh.

echo Stopping any running Python/Node processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

:: echo Clearing Reflex cache (.web folder)...
:: if exist ".web" rmdir /s /q ".web"

echo Starting Server...
cd /d "%~dp0"
call ..\.venv\Scripts\activate

echo Opening browser in 5 seconds...
start /b cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:3000"

reflex run

pause
