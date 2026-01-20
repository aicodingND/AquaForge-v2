@echo off
setlocal
echo ==================================================
echo   AquaForge E2E Auto-Verification
echo ==================================================

set "VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe"
set "PROJECT_ROOT=%~dp0"

echo [TEST] Check if server is reachable?
echo (Assuming server is running via run_app_optimized.bat)

:: Run the test
set PYTHONPATH=%PROJECT_ROOT%
cd /d "%PROJECT_ROOT%swim_ai_reflex"
"%VENV_PYTHON%" tests/test_e2e_demo.py

if %errorlevel% equ 0 (
    echo [SUCCESS] E2E Walkthrough Passed!
    color 0A
) else (
    echo [FAILURE] E2E Walkthrough Failed. Check logs.
    color 0C
)

pause
endlocal
