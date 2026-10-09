@echo off
title SafeVision AI - Industrial Safety Command Center
color 0A
cd /d "%~dp0"
echo =====================================================================
echo    SAFEVISION AI - INDUSTRIAL SAFETY COMMAND CENTER
echo    STPI & EmTek BPUT Hackathon Project
echo =====================================================================
echo.
echo Starting SafeVision AI Server...
echo Opening Dashboard in your browser...
echo.

:: Automatically open the dashboard in default browser after 2 seconds
start /min cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Start AI Server
python run.py

pause
