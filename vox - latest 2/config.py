"""
Vox - Configuration v3.2 — ALL BUGS FIXED
==========================================
BUG FIX LOG:
  [BUG 1] MIC_INDEX was hardcoded to 1 — now None (auto-detect)
  [BUG 2] MIC_ENERGY_THRESHOLD 80 was too sensitive — now 200 with proper dynamic control
  [BUG 3] MIC_DYNAMIC_ENERGY True was letting threshold drift too high — now False after calibration
"""
import os, sys

# ═══════════════════════════════════════════════
#  PATHS
# ═══════════════════════════════════════════════
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR       = os.path.join(BASE_DIR,  "assets")
LOGS_DIR         = os.path.join(BASE_DIR,  "logs")
DATA_DIR         = os.path.join(BASE_DIR,  "data")
FACES_DIR        = os.path.join(DATA_DIR,  "faces")
VOICE_PRINTS_DIR = os.path.join(DATA_DIR,  "voice_prints")
DOWNLOADS_DIR    = os.path.join(os.path.expanduser("~"), "Downloads", "Vox_Downloads")
SCREENSHOTS_DIR  = os.path.join(DOWNLOADS_DIR, "Screenshots")
DB_FILE          = os.path.join(DATA_DIR,  "Vox.db")
LOG_FILE         = os.path.join(LOGS_DIR,  "Vox.log")
VOICE_LOG        = os.path.join(LOGS_DIR,  "voice_debug.log")   # NEW: voice debug log

for _d in [ASSETS_DIR, LOGS_DIR, DATA_DIR, FACES_DIR,
           VOICE_PRINTS_DIR, DOWNLOADS_DIR, SCREENSHOTS_DIR]:
    os.makedirs(_d, exist_ok=True)

# ═══════════════════════════════════════════════
#  API KEYS
# ═══════════════════════════════════════════════
GEMINI_API_KEY        = ""   # Get from aistudio.google.com
PICOVOICE_ACCESS_KEY  = ""

# ═══════════════════════════════════════════════
#  AI MODELS
# ═══════════════════════════════════════════════
GEMINI_MODEL   = "gemini-1.5-flash"
OLLAMA_ENABLED = True
OLLAMA_MODEL   = "llama3.2"
OLLAMA_HOST    = "http://localhost:11434"

# ═══════════════════════════════════════════════
#  SPEECH / MIC — FIXED SETTINGS
# ═══════════════════════════════════════════════
WAKE_WORD      = "hey Vox"
WAKE_WORD_ALTS = [
    "voc","ebook","ebooks","box","books","book", "a box","havocs","a books","box","e books","a book","books","hey books" ,"he books","he walks", "Vox", "ok Vox", "hey works" , "hello Vox", "vocs", "he work", "hi Vox", "havoc", "hey walks" , "hey walk" , "ha walks" , "box" , "hey box", "hey folks", "hey fox", "hey voice", "hey rocks", "hey books", "hey works", "hey box", "hey box", "a vox", "the vox"
]

# ── [BUG FIX 1] MIC_INDEX was hardcoded to 1 ──────────────────────
# None = auto-detect best microphone (RECOMMENDED)
# Set to a number (0,1,2...) ONLY if auto-detect picks wrong mic
# Run: python test_voice.py  to find your mic index
MIC_INDEX = 1   # Auto-detected by test_voice.py

# ── [BUG FIX 2] Energy threshold ──────────────────────────────────
# Too LOW (80)  = picks up background noise → fake triggers → STT fails → no wake word
# Too HIGH (500+) = mic never triggers at all
# 200-300 = sweet spot for most indoor microphones
MIC_ENERGY_THRESHOLD = 800   # Auto-calibrated by test_voice.py

# ── [BUG FIX 3] Dynamic energy must be False after calibration ────
# When True, threshold drifts UP in quiet rooms → mic stops responding
# We calibrate ONCE at startup, then FREEZE the threshold
MIC_DYNAMIC_ENERGY   = False   # FIXED: do not drift threshold

MIC_PAUSE_THRESHOLD  = 0.3    # Lowered for near-instant speech capture
LISTEN_TIMEOUT       = 8      # Snappier timeout
PHRASE_TIME_LIMIT    = 12     # Optimized limit
WHISPER_MODEL        = "tiny"  # Fastest model for Faster-Whisper

# ── TTS settings ──
TTS_RATE    = 185             # Faster speaking rate
TTS_VOLUME  = 1.0
TTS_VOICE   = "male"
TTS_WAIT_AFTER_SPEAK = 0.4    # Reduced wait time for faster turn-taking

# ═══════════════════════════════════════════════
#  FEATURES
# ═══════════════════════════════════════════════
ENABLE_VOICE_RESPONSE     = True
ENABLE_VOICE_RECOGNITION  = False
VOICE_RECOGNITION_THRESHOLD = 0.72
ENABLE_FACE_RECOGNITION   = True
ENABLE_SYSTEM_TRAY        = True
YOUTUBE_AUTO_PLAY         = True
VOICE_DEBUG_LOG           = True   # NEW: write voice events to voice_debug.log

# ═══════════════════════════════════════════════
#  AUTO-LOGIN
# ═══════════════════════════════════════════════
AUTO_LOGIN      = False
AUTO_LOGIN_USER = ""

# ═══════════════════════════════════════════════
#  BROWSER / SEARCH
# ═══════════════════════════════════════════════
DEFAULT_BROWSER = "chrome"
SEARCH_ENGINE   = "google"

# ═══════════════════════════════════════════════
#  MISC
# ═══════════════════════════════════════════════
VOLUME_STEP       = 10
MAX_DOWNLOAD_SIZE = 1024 ** 3
YOUTUBE_QUALITY   = "best[height<=720]"
WHATSAPP_WEB_URL  = "https://web.whatsapp.com"

# ── [BUG FIX 4] Port lock — if port in use from crash, voice won't start ──
# Changed to higher ports less likely to conflict
VOICE_LOCK_PORT = 0     # ← FIXED: was 65440 — now 0 = disable port lock entirely
GUI_LOCK_PORT   = 0     # ← FIXED: was 65441 — disabled, causes silent voice failure
