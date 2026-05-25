@echo off
title Vox AI Assistant
cd /d "%~dp0"

echo.
echo  ██╗   ██╗ ██████╗ ██╗  ██╗
echo  ██║   ██║██╔═══██╗╚██╗██╔╝
echo  ██║   ██║██║   ██║ ╚███╔╝
echo  ╚██╗ ██╔╝██║   ██║ ██╔██╗
echo   ╚████╔╝ ╚██████╔╝██╔╝ ██╗
echo    ╚═══╝   ╚═════╝ ╚═╝  ╚═╝
echo.
echo  Advanced AI Voice Assistant v3.2
echo  ----------------------------------
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Run setup_fixed.bat first.
    pause & exit /b 1
)

REM Check if test has been run
if not exist "logs\voice_debug.log" (
    echo [IMPORTANT] First time setup detected.
    echo.
    echo Run test_voice.py first to configure your microphone:
    echo   python test_voice.py
    echo.
    set /p CONT="Press Enter to start anyway, or Ctrl+C to run test first: "
)

echo Starting Vox...
echo Voice events will be logged to: logs\voice_debug.log
echo.
echo If you don't hear Vox respond:
echo   1. Check logs\voice_debug.log
echo   2. Run: python test_voice.py
echo   3. Check Windows mic permissions
echo.

python main.py

REM If there's an error, show it (DON'T hide console on error)
if errorlevel 1 (
    echo.
    echo [ERROR] Vox crashed. See error above.
    echo Check logs\voice_debug.log for voice-specific issues.
    pause
)


