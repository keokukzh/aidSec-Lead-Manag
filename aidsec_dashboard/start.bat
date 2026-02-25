@echo off
echo ============================================
echo   AidSec Lead Dashboard - Starting...
echo ============================================
echo.

cd /d "%~dp0"

:: Kill stale processes on our ports
echo [*] Cleaning up stale processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr LISTENING') do (
    taskkill //f //pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501" ^| findstr LISTENING') do (
    taskkill //f //pid %%a >nul 2>&1
)
timeout /t 2 /nobreak > nul

echo [*] Starting API on port 8000...
start "AidSec API" cmd //k "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak > nul

echo [*] Starting Streamlit UI on port 8501...
start "AidSec UI" cmd //k "python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --browser.gatherUsageStats false"

timeout /t 3 /nobreak > nul

echo.
echo ============================================
echo   Dashboard starting...
echo.
echo   UI:  http://localhost:8501
echo   API: http://localhost:8000/api/docs
echo ============================================
echo.

:: Auto-open browser
start "" http://localhost:8501

echo Press any key to exit (services keep running)...
pause > nul
