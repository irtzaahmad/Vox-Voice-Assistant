@echo off
title Vox JARVIS Assistant
cd /d "%~dp0"

:menu
cls
echo ==========================================
echo       VOX JARVIS ASSISTANT v5.1
echo ==========================================
echo  1. Start Voice Mode (Background Listening)
echo  2. Start Text Mode (Type Commands)
echo  3. Install/Update Dependencies
echo  4. Exit
echo ==========================================
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto voice
if "%choice%"=="2" goto text
if "%choice%"=="3" goto install
if "%choice%"=="4" goto exit

:voice
echo Starting Voice Mode...
python main.py
pause
goto menu

:text
echo Starting Text Mode...
python main.py --text
pause
goto menu

:install
echo Installing Dependencies...
python install_dependencies.py
pause
goto menu

:exit
exit