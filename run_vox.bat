@echo off
title Vox Assistant

echo ====================================
echo  Vox v5.1 — Groq Cloud Edition
echo ====================================

cd /d "%~dp0"
python main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] Vox failed to start.
    echo         Make sure you have installed dependencies:
    echo         pip install -r requirements.txt
    pause
)
