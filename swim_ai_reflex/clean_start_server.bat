@echo off
:: AquaForge Clean Start Script (Inner Directory)
:: Use this if the app is acting weird or not updating correctly.
:: It deletes the cache and recompiles everything from scratch.

echo Stopping any running Python/Node processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1

echo Clearing Reflex cache (.web folder)...
if exist ".web" rmdir /s /q ".web"

echo Starting Server (Fresh Build)...
cd /d "%~dp0"
call ..\..\.venv\Scripts\activate

echo Opening browser in 5 seconds...
start /b cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:3000"

reflex run

pause
