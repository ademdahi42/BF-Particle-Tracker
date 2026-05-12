@echo off
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if not exist "%APP_DIR%.venv_app\Scripts\python.exe" (
    echo BF-Particle-Tracker is not installed yet.
    echo Run installer\install.bat first.
    pause
    exit /b 1
)

"%APP_DIR%.venv_app\Scripts\python.exe" "%APP_DIR%main.py"
if errorlevel 1 (
    echo.
    echo The application closed with an error.
    pause
)
