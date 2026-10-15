@echo off
title EVA - J.A.R.V.I.S Assistant
cd /d "%~dp0"
echo ========================================================
echo        STARTING EVA / JARVIS MULTIMODAL ASSISTANT
echo ========================================================
echo Checking system components...
python setup_check.py
echo.
echo Launching Dashboard and Real-Time Voice Assistant...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)
