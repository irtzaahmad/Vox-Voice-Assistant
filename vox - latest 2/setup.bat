@echo off
echo =====================================================
echo   Vox v3.0 - AI Desktop Assistant Setup
echo =====================================================
echo.
python --version >nul 2>&1 || (echo Python not found! & pause & exit /b)
echo [OK] Python found
echo.
echo [1/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [2/6] Speech Recognition...
pip install SpeechRecognition PyAudioWPatch --quiet
echo [3/6] TTS + AI...
pip install pyttsx3 google-generativeai ollama --quiet
echo [4/6] GUI + System...
pip install customtkinter Pillow pyautogui psutil pywin32 pycaw --quiet
echo [5/6] Web + Downloads...
pip install requests yt-dlp beautifulsoup4 pystray --quiet
echo [6/6] Utilities...
pip install pyyaml --quiet
echo.
echo Creating folders...
if not exist "data"   mkdir data
if not exist "logs"   mkdir logs
if not exist "assets" mkdir assets
echo.
echo =====================================================
echo   DONE! 
echo.
echo   1. Add your Gemini API key in config.py
echo      Get FREE key: https://aistudio.google.com
echo.
echo   2. Launch Vox:
echo      Double-click  launcher.pyw  (no console)
echo      Or run:       Vox.bat
echo.
echo   OPTIONAL - Face Recognition:
echo      pip install cmake dlib face_recognition opencv-python
echo =====================================================
pause


