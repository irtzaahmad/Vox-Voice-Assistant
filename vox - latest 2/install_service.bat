@echo off
REM Vox v2.1 - Background Service Installer
REM Finds NSSM automatically in Downloads or current folder

echo.
echo ===================================================
echo   Vox v2.1 - Background Service Installer
echo ===================================================
echo.

REM ── Try to find NSSM ──
set NSSM=
if exist "%~dp0nssm.exe"                          set NSSM="%~dp0nssm.exe"
if exist "%USERPROFILE%\Downloads\nssm.exe"       set NSSM="%USERPROFILE%\Downloads\nssm.exe"
if exist "%USERPROFILE%\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe" ^
    set NSSM="%USERPROFILE%\Downloads\nssm-2.24\nssm-2.24\win64\nssm.exe"

if "%NSSM%"=="" (
    echo [ERROR] NSSM not found.
    echo Download from: https://nssm.cc/download
    echo Extract nssm.exe into this Vox folder, then run again.
    pause
    exit /b 1
)

echo [OK] NSSM found: %NSSM%
echo.

REM ── Find python.exe ──
for /f "tokens=*" %%i in ('where python') do (set PY=%%i & goto :found_py)
:found_py
echo [OK] Python: %PY%
echo.

set SCRIPT="%~dp0main.py"
set DIR="%~dp0"

echo [1/4] Removing old service (if any)...
%NSSM% stop  Vox_Core 2>nul
%NSSM% remove Vox_Core confirm 2>nul

echo [2/4] Installing Vox_Core service...
%NSSM% install Vox_Core "%PY%" "%~dp0main.py" --service

echo [3/4] Configuring service...
%NSSM% set Vox_Core AppDirectory %DIR%
%NSSM% set Vox_Core DisplayName  "Vox Voice Assistant"
%NSSM% set Vox_Core Description  "Always-On voice recognition — Hey Vox"
%NSSM% set Vox_Core Start        SERVICE_AUTO_START
%NSSM% set Vox_Core AppStdout    "%~dp0logs\service_out.log"
%NSSM% set Vox_Core AppStderr    "%~dp0logs\service_err.log"

echo [4/4] Starting service...
%NSSM% start Vox_Core

echo.
echo ===================================================
echo   SUCCESS!
echo   Vox is now a background Windows service.
echo   It starts automatically with Windows.
echo   Launch the GUI anytime with Vox.bat
echo ===================================================
echo.
pause


