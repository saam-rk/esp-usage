@echo off
rem Double-click this file to start sending usage data to the ESP32 display.
rem Optional: pass a COM port to skip auto-detection, for example: start-bridge.bat COM5
title esp-usage bridge
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up Python for the bridge. This takes about a minute...
    py -3 -m venv .venv || goto :setup_failed
)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r bridge\requirements.txt || goto :setup_failed

".venv\Scripts\python.exe" bridge\bridge.py %*
echo.
pause
exit /b

:setup_failed
echo.
echo Setup failed. Make sure Python 3 is installed: https://www.python.org/downloads/
pause
exit /b 1
