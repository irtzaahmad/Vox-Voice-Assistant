@echo off
title Vox v3.2 - Fixed Setup
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   Vox v3.2 - Complete Fix Setup                 ║
echo ║   All 5 bugs fixed - Voice will work now        ║
echo ╚══════════════════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install Python 3.10+ from python.org
    echo Make sure to check "Add Python to PATH"
    pause & exit /b 1
)
echo [OK] Python found
echo.

echo [1/8] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo.
echo [2/8] CRITICAL FIX: NumPy pinned to compatible version...
pip install "numpy>=1.24,<2.0" --quiet

echo.
echo [3/8] Speech Recognition + PyAudioWPatch...
pip install SpeechRecognition --quiet
pip install PyAudioWPatch --quiet

if errorlevel 1 (
    echo PyAudioWPatch pip failed - trying alternative...
    python -m pip install PyAudioWPatch
)

echo.
echo [4/8] Text-to-Speech...
pip install pyttsx3 --quiet

echo.
echo [5/8] AI + NLP...
pip install google-generativeai ollama spacy --quiet
python -m spacy download en_core_web_sm --quiet 2>nul

echo.
echo [6/8] GUI + System...
pip install customtkinter Pillow pyautogui psutil pywin32 pycaw --quiet

echo.
echo [7/8] Web + Downloads...
pip install requests yt-dlp beautifulsoup4 pystray --quiet

echo.
echo [8/8] Audio libs (for voice enrollment)...
pip install librosa soundfile bcrypt --quiet
pip install pyyaml screen-brightness-control --quiet

echo.
echo Creating folders...
if not exist "data"        mkdir data
if not exist "logs"        mkdir logs
if not exist "assets"      mkdir assets
if not exist "core"        mkdir core
if not exist "modules"     mkdir modules
if not exist "gui"         mkdir gui
if not exist "data\faces"  mkdir data\faces
if not exist "data\voice_prints" mkdir data\voice_prints

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   Installation Complete!                        ║
echo ╠══════════════════════════════════════════════════╣
echo ║                                                 ║
echo ║   NEXT STEPS (in order):                        ║
echo ║                                                 ║
echo ║   1. FIRST run the voice test:                  ║
echo ║      python test_voice.py                       ║
echo ║      (auto-detects your mic and fixes config)   ║
echo ║                                                 ║
echo ║   2. Add your Gemini API key in config.py:      ║
echo ║      GEMINI_API_KEY = "your-key-here"           ║
echo ║      Get FREE key: aistudio.google.com          ║
echo ║                                                 ║
echo ║   3. Start Vox:                                 ║
echo ║      Double-click Vox.bat                       ║
echo ║      OR: python main.py                         ║
echo ║                                                 ║
echo ║   4. If voice still not working:                ║
echo ║      Check logs\voice_debug.log                 ║
echo ║      (all voice events logged there)            ║
echo ║                                                 ║
echo ╚══════════════════════════════════════════════════╝
echo.
pause


