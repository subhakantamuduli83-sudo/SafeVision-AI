@echo off
title Stop SafeVision AI - Shutdown
color 0C
cd /d "%~dp0"
echo =====================================================================
echo    STOPPING SAFEVISION AI COMMAND CENTER
echo =====================================================================
echo.
echo Shutting down AI vision engine and server processes on port 8000...

:: Terminate process listening on port 8000 (SafeVision AI / Uvicorn)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo [OK] SafeVision AI server has been completely closed!
echo Window closing in 2 seconds...
timeout /t 2 /nobreak >nul
exit
