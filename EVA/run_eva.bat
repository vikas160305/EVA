@echo off
title EVA - J.A.R.V.I.S Assistant
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    )
)
echo ========================================================
echo        STARTING EVA / JARVIS MULTIMODAL ASSISTANT
echo ========================================================
echo Checking system components...
%PY% setup_check.py
echo.
echo Launching Dashboard and Real-Time Voice Assistant...
%PY% main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
    pause
)
