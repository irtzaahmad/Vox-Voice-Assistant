# Vox v3.2 — Bug Report & Fix Documentation

## ❌ Problem: "Hey Vox" sun hi nahi raha

Saare 5 root causes dhundh liye gaye aur fix kar diye gaye.

---

## 🐛 BUG 1 — Port Lock Silent Failure (CRITICAL)

**File:** `main.py`

**Original Code:**
```python
def _lock(port):
    try:
        s = socket.socket(...)
        s.bind(('127.0.0.1', port))
        return s
    except OSError:
        return None   # ← Port in use → returns None

class Vox:
    def __init__(self, voice_lock=None):
        self.voice_lock = voice_lock or _lock(config.VOICE_LOCK_PORT)
        # ↑ If port 65440 was in use from previous crash → voice_lock = None
        
        self.voice_engine = AlwaysOnVoiceEngine(self) if self.voice_lock else None
        # ↑ voice_lock is None → voice_engine = NONE → NO VOICE AT ALL
```

**What happened:** Agar Vox pehle crash hua aur port 65440 release nahi hua, toh agali baar `voice_engine` hi nahi banta. Koi error nahi, koi warning nahi — buss voice silently dead.

**Fix:**
```python
# Port lock completely removed
# voice_engine ALWAYS created
self.voice_engine = AlwaysOnVoiceEngine(self)
```

---

## 🐛 BUG 2 — FreeConsole() Hid All Errors

**File:** `main.py`

**Original Code:**
```python
if sys.platform == "win32":
    ctypes.WinDLL('kernel32').FreeConsole()  # ← Kills ALL output
```

**What happened:** Yeh line saare `print()` statements aur error messages hide kar deta tha. Jab voice engine crash hota, toh koi bhi error visible nahi hoti. Debugging impossible.

**Fix:** FreeConsole() removed. Ab saari voice events `logs/voice_debug.log` mein jaati hain.

---

## 🐛 BUG 3 — TTS Bleeding Into Microphone (CRITICAL)

**File:** `core/always_on_voice.py`

**Original Code:**
```python
# Phase 1: Wake word detected!
self.app.speaker.speak("Yes?")   # ← TTS starts in background thread

# Phase 2: IMMEDIATELY listen for command (mic still open!)
audio_cmd = self._rec.listen(source, ...)
# ↑ Mic captures TTS saying "Yes?" and sends it to STT
# STT returns "yes" → not a valid command → loop continues
# User thinks Vox didn't respond to wake word
```

**What happened:** Vox ka "Yes?" TTS audio microphone mein ja raha tha. STT "yes" sunti, command nahi milta, loop continue. User ko lagta tha Vox deaf hai.

**Fix:**
```python
self.app.speaker.speak("Yes?")
time.sleep(config.TTS_WAIT_AFTER_SPEAK)  # ← 1.2 seconds wait
# TTS finish hone ke baad hi mic khulta hai
audio_cmd = self._rec.listen(source, ...)
```

---

## 🐛 BUG 4 — Dynamic Energy Threshold Drift (CRITICAL)

**File:** `config.py` + `core/always_on_voice.py`

**Original Code:**
```python
MIC_ENERGY_THRESHOLD = 80        # Too low
MIC_DYNAMIC_ENERGY   = True      # ← Auto-adjustment ON

# In voice loop:
self._rec.adjust_for_ambient_noise(source, duration=1.5)
# ↑ In a quiet room, this can set threshold to 30-50
# ↑ With dynamic=True, it keeps auto-adjusting
# ↑ If environment gets slightly louder, threshold shoots up to 600+
# ↑ Mic stops detecting speech
```

**What happened:** `dynamic_energy_threshold=True` matlb threshold khud adjust hota rehta hai. Quiet room mein calibrate karo, toh threshold bahut low set hota hai. Phir koi awaaz aaye toh dynamically bahut high jump karta hai. Result: mic kabhi nahi triggers.

**Fix:**
```python
MIC_ENERGY_THRESHOLD = 200       # Sane default
MIC_DYNAMIC_ENERGY   = False     # FREEZE after calibration

# After calibrate:
calibrated = adjust_for_ambient_noise(...)
threshold  = max(150, min(400, calibrated))  # Clamp to sane range
rec.dynamic_energy_threshold = False          # Don't drift!
```

---

## 🐛 BUG 5 — MIC_INDEX Hardcoded Wrong

**File:** `config.py`

**Original Code:**
```python
MIC_INDEX = 1   # ← Hardcoded! May not exist on all PCs
```

**What happened:** Index 1 kisi PC pe output device ho sakta hai, kisi pe mute mic, kisi pe exist hi nahi karta. Wrong index pe koi audio nahi aata.

**Fix:**
```python
MIC_INDEX = None   # ← Auto-detect best microphone

# In voice engine:
# Tests each mic one by one
# Prefers mics with "microphone", "input", "realtek" in name
# Skips output devices (speaker, stereo mix)
# Saves working index to config.py via test_voice.py
```

---

## 🐛 BUG 6 — No Offline STT Fallback

**File:** `core/always_on_voice.py`

**Original Code:**
```python
try:
    text = rec.recognize_google(audio)
    return text.lower()
except RequestError:
    pass   # ← Google offline → returns "" → wake word never detected
```

**What happened:** Internet nahi hai ya Google block hai toh completely silent failure. No fallback.

**Fix:**
```python
# 1. Try Google (online)
# 2. Try Whisper (offline local)  ← NEW
# 3. Try Sphinx (offline basic)   ← NEW
# If all fail → empty string (graceful)
```

---

## ✅ Summary of Changes

| File | Change |
|------|--------|
| `config.py` | MIC_INDEX=None, ENERGY=200, DYNAMIC=False, PORT_LOCK=0 |
| `main.py` | Removed FreeConsole(), removed port lock, voice always starts |
| `core/always_on_voice.py` | Complete rewrite: listen_in_background, auto mic detect, calibration clamp, TTS wait, file logging |
| `core/speaker.py` | Added speak_and_wait(), is_speaking property |
| `test_voice.py` | NEW: Full diagnostic, auto-detects mic, updates config.py |
| `Vox.bat` | Shows errors instead of hiding them |
| `setup_fixed.bat` | Updated with correct install order |

---

## 🚀 HOW TO USE

```
Step 1: setup_fixed.bat    ← Install all packages
Step 2: python test_voice.py   ← Find your mic, test wake word
Step 3: Vox.bat            ← Start Vox

If voice still not working:
  Check: logs\voice_debug.log   ← All voice events logged here
```

---

## 📋 voice_debug.log Sample (what you should see)

```
[10:30:01] ▶  Voice engine starting…
[10:30:01] ✅ SR initialized. Energy threshold: 200
[10:30:01] 🎤 Available microphones (3):
[10:30:01]    [0] Microsoft Sound Mapper - Input
[10:30:01]    [1] Microphone (Realtek Audio)
[10:30:01]    [2] Stereo Mix (Realtek Audio)
[10:30:01]    Testing [1] Microphone (Realtek Audio)… ✅ WORKS
[10:30:01] ✅ Using microphone index 1
[10:30:02] 🔧 Calibrating microphone…
[10:30:03] ✅ Calibration done. Raw: 187 → Clamped: 187
[10:30:03] ✅ Background listener active!
[10:30:03] SAY 'HEY Vox' TO ACTIVATE
[10:30:08] 👂 Heard (bg): 'hey Vox'
[10:30:08] 🟢 WAKE WORD DETECTED!
[10:30:09] 🎤 Listening for command…
[10:30:12] 📝 Command recognized: 'what time is it'
[10:30:12] 🤖 Processing: 'what time is it'
[10:30:12] 💬 Response: 'It's 10:30 AM.'
```


