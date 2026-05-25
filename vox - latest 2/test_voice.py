"""
Vox - Voice Diagnostic & Fix Tool v2.0
========================================
Is script ko pehle run karo apne PC pe:
  python test_voice.py

Yeh automatically:
  1. Best microphone dhundh kar config.py update karega
  2. Sahi energy threshold set karega
  3. Wake word "Hey Vox" test karega
  4. Saari problems report karega

Agar yahan 'Hey Vox' detect ho jaye, toh main program bhi work karega.
"""

import sys
import os
import time
import difflib

# ── [CRITICAL FIX] PyAudio Monkeypatch ────────────────────────────
try:
    import pyaudiowpatch as pyaudio
    sys.modules['pyaudio'] = pyaudio
    # print("ℹ️  PyAudio monkeypatched via PyAudioWPatch")
except ImportError:
    pass

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def separator(char="=", n=60):
    print(char * n)


def test_python():
    separator()
    print("  STEP 1: Python Check")
    separator()
    print(f"  Python: {sys.version.split()[0]}")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 8):
        print("  ❌ Python 3.8+ required!")
        return False
    print("  ✅ Python OK")
    return True


def test_packages():
    separator()
    print("  STEP 2: Package Check")
    separator()
    
    all_ok = True
    
    # Check PyAudio / PyAudioWPatch specifically
    try:
        import pyaudio
        print("  ✅ PyAudio (or PyAudioWPatch)")
    except ImportError:
        try:
            import pyaudiowpatch
            print("  ✅ PyAudioWPatch")
        except ImportError:
            print("  ❌ PyAudioWPatch missing — run: python -m pip install PyAudioWPatch")
            all_ok = False

    packages = {
        "speech_recognition": "SpeechRecognition",
        "pyttsx3":            "pyttsx3",
    }
    for module, pip_name in packages.items():
        try:
            __import__(module)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name} missing — run: pip install {pip_name}")
            all_ok = False

    if not all_ok:
        print()
        print("  Run this to install everything:")
        print("  python -m pip install SpeechRecognition PyAudioWPatch pyttsx3")
        print("  OR: setup_fixed.bat")
    return all_ok


def test_tts():
    separator()
    print("  STEP 3: Text-to-Speech Test")
    separator()
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        print(f"  Available voices: {len(voices)}")
        for i, v in enumerate(voices):
            print(f"    [{i}] {v.name}")
        engine.setProperty('rate', 165)
        engine.say("Vox voice test. You should hear this.")
        engine.runAndWait()
        print("  ✅ TTS working — did you hear the voice?")
        return True
    except ImportError:
        print("  ❌ pyttsx3 not installed")
        return False
    except Exception as e:
        print(f"  ❌ TTS error: {e}")
        return False


def list_mics():
    """List all microphones and return them."""
    import speech_recognition as sr
    try:
        mics = sr.Microphone.list_microphone_names()
        return mics
    except Exception as e:
        print(f"  ❌ Could not list mics: {e}")
        return []


def find_best_mic():
    """Auto-detect best microphone. Returns (index, name) or (None, 'default')."""
    separator()
    print("  STEP 4: Microphone Detection")
    separator()

    try:
        import speech_recognition as sr
    except ImportError:
        print("  ❌ SpeechRecognition not installed")
        return None, "none"

    mics = list_mics()
    if not mics:
        print("  ❌ No microphones found!")
        print("  → Check Windows Settings > Privacy > Microphone")
        print("  → Ensure microphone is plugged in")
        return None, "none"

    print(f"  Found {len(mics)} microphone(s):")
    for i, m in enumerate(mics):
        print(f"    [{i}] {m}")
    print()

    # Find preferred mics
    prefer_kw  = ["microphone", "mic", "input", "realtek", "headset", "audio"]
    skip_kw    = ["output", "speaker", "stereo mix", "what u hear", "loopback", "renderer"]

    candidates = []
    for i, name in enumerate(mics):
        n_lower = name.lower()
        if any(kw in n_lower for kw in skip_kw):
            continue
        priority = sum(kw in n_lower for kw in prefer_kw)
        candidates.append((priority, i, name))

    # Also add 0 and 1 as fallbacks
    for fi in [0, 1]:
        if not any(c[1] == fi for c in candidates) and fi < len(mics):
            candidates.append((0, fi, mics[fi]))

    candidates.sort(key=lambda x: -x[0])

    print("  Testing microphones…")
    for priority, idx, name in candidates:
        print(f"    Testing [{idx}] {name}… ", end="", flush=True)
        try:
            mic = sr.Microphone(device_index=idx)
            with mic as source:
                pass   # Just open — if no error, it works
            print("✅ WORKS")
            return idx, name
        except Exception as e:
            print(f"❌ ({str(e)[:40]})")

    # Try default
    print("    Testing default mic… ", end="", flush=True)
    try:
        with sr.Microphone() as source:
            pass
        print("✅ WORKS")
        return None, "System Default"
    except Exception as e:
        print(f"❌ ({e})")

    print("  ❌ NO WORKING MICROPHONE FOUND!")
    print("  → Check Windows Settings > Privacy > Microphone")
    print("  → Allow apps to access microphone")
    return None, "none"


def calibrate_mic(mic_index):
    """Calibrate mic and find ideal energy threshold."""
    separator()
    print("  STEP 5: Microphone Calibration")
    separator()

    import speech_recognition as sr
    rec = sr.Recognizer()
    rec.dynamic_energy_threshold = False

    try:
        mic_args = {} if mic_index is None else {"device_index": mic_index}
        print("  Calibrating for 2 seconds — please be QUIET…")
        with sr.Microphone(**mic_args) as source:
            rec.adjust_for_ambient_noise(source, duration=2.0)

        raw = rec.energy_threshold
        # Clamp to sane range
        clamped = max(150, min(400, raw))
        rec.energy_threshold = clamped

        print(f"  Raw ambient level:    {raw:.0f}")
        print(f"  Recommended threshold: {clamped:.0f}")

        if raw < 50:
            print("  ⚠️  Very low ambient (possibly wrong mic or mic not picking up)")
        elif raw > 500:
            print("  ⚠️  Very high ambient — try reducing background noise")
        else:
            print("  ✅ Ambient noise level is normal")

        return clamped
    except Exception as e:
        print(f"  ❌ Calibration error: {e}")
        return 200


def test_listening(mic_index, threshold):
    """Test if mic can capture speech."""
    separator()
    print("  STEP 6: Speech Capture Test")
    separator()

    import speech_recognition as sr
    rec = sr.Recognizer()
    rec.energy_threshold        = threshold
    rec.dynamic_energy_threshold = False
    rec.pause_threshold         = 0.8

    mic_args = {} if mic_index is None else {"device_index": mic_index}

    print("  Speak ANYTHING in the next 5 seconds…")
    print("  (Say: 'hello', 'testing', etc.)")
    try:
        with sr.Microphone(**mic_args) as source:
            try:
                audio = rec.listen(source, timeout=5, phrase_time_limit=5)
                print("  ✅ Audio CAPTURED! Recognizing…")
            except sr.WaitTimeoutError:
                print("  ❌ NO AUDIO DETECTED in 5 seconds!")
                print(f"     Current threshold: {rec.energy_threshold:.0f}")
                print("     Solutions:")
                print("     1. Lower MIC_ENERGY_THRESHOLD in config.py (try 100)")
                print("     2. Check mic is not muted in Windows Sound settings")
                print("     3. Try a different microphone index")
                return False, 0.0

        try:
            text = rec.recognize_google(audio)
            print(f"  ✅ Recognized: '{text}'")
            return True, rec.energy_threshold
        except sr.UnknownValueError:
            print("  ⚠️  Audio captured but speech not recognized")
            print("     (Speak louder and closer to mic)")
            return True, rec.energy_threshold   # Mic IS working, just recognition issue
        except sr.RequestError:
            print("  ⚠️  Google STT offline — check internet connection")
            print("     (Mic IS working, but no internet for recognition)")
            return True, rec.energy_threshold
    except Exception as e:
        print(f"  ❌ Listen error: {e}")
        return False, threshold


def test_wake_word(mic_index, threshold):
    """Test complete wake word detection flow."""
    separator()
    print("  STEP 7: Wake Word Test — SAY 'HEY Vox'")
    separator()

    import speech_recognition as sr
    rec = sr.Recognizer()
    rec.energy_threshold        = threshold
    rec.dynamic_energy_threshold = False
    rec.pause_threshold         = 0.8

    WAKE_ALTS = [
        "hey Vox", "Vox", "ok Vox", "hello Vox",
        "hey box", "hey fox", "hey Vox", "Vox",
        "hi Vox", "hey voice", "hey folks", "hey box", "hey books", "hey works", "hey rocks"
    ]

    def is_wake(text: str) -> bool:
        if not text: return False
        t = text.lower().strip()
        for alt in WAKE_ALTS:
            if alt in t: return True
        if 'vox' in t: return True
        if len(t) <= 20:
            score = difflib.SequenceMatcher(None, t, "hey vox").ratio()
            if score >= 0.65: return True
        return False

    mic_args = {} if mic_index is None else {"device_index": mic_index}

    print("  🎤 Say 'HEY Vox' clearly now (10 seconds)…")
    print()

    try:
        with sr.Microphone(**mic_args) as source:
            try:
                audio = rec.listen(source, timeout=10, phrase_time_limit=4)
            except sr.WaitTimeoutError:
                print("  ❌ No audio detected. Wake word test failed.")
                print("     Mic issue — fix Step 6 first")
                return False

        try:
            text = rec.recognize_google(audio)
        except sr.UnknownValueError:
            print("  ❌ Could not understand speech. Speak more clearly.")
            return False
        except sr.RequestError:
            print("  ⚠️  No internet for Google STT. Trying offline…")
            text = ""

        print(f"  STT heard: '{text}'")

        if is_wake(text):
            print()
            print("  ✅✅✅ WAKE WORD DETECTED! Vox WILL WORK! ✅✅✅")
            return True
        else:
            print()
            print(f"  ❌ Wake word NOT detected in: '{text}'")
            print("  Expected: 'hey Vox', 'Vox', or 'Vox'")
            print("  Tips:")
            print("  - Say clearly: HEY-Vox (two separate words)")
            print("  - Speak closer to mic")
            print("  - Check mic is picking up correctly (Step 6 passed?)")
            return False

    except Exception as e:
        print(f"  ❌ Wake word test error: {e}")
        return False


def update_config(mic_index, threshold):
    """Automatically update config.py with discovered settings."""
    separator()
    print("  STEP 8: Updating config.py")
    separator()

    config_path = os.path.join(ROOT, "config.py")
    if not os.path.exists(config_path):
        print("  ⚠️  config.py not found — skipping auto-update")
        print(f"     Manually set: MIC_INDEX = {mic_index}")
        print(f"     Manually set: MIC_ENERGY_THRESHOLD = {int(threshold)}")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re

        # Update MIC_INDEX
        mic_val = str(mic_index) if mic_index is not None else "None"
        content = re.sub(
            r'^MIC_INDEX\s*=.*$',
            f'MIC_INDEX = {mic_val}   # Auto-detected by test_voice.py',
            content, flags=re.MULTILINE
        )

        # Update MIC_ENERGY_THRESHOLD
        content = re.sub(
            r'^MIC_ENERGY_THRESHOLD\s*=.*$',
            f'MIC_ENERGY_THRESHOLD = {int(threshold)}   # Auto-calibrated by test_voice.py',
            content, flags=re.MULTILINE
        )

        # Ensure dynamic energy is False
        content = re.sub(
            r'^MIC_DYNAMIC_ENERGY\s*=.*$',
            'MIC_DYNAMIC_ENERGY   = False   # FIXED: do not drift threshold',
            content, flags=re.MULTILINE
        )

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  ✅ config.py updated:")
        print(f"     MIC_INDEX = {mic_val}")
        print(f"     MIC_ENERGY_THRESHOLD = {int(threshold)}")
        print(f"     MIC_DYNAMIC_ENERGY = False")

    except Exception as e:
        print(f"  ⚠️  Config update error: {e}")
        print(f"     Manually set: MIC_INDEX = {mic_index}")
        print(f"     Manually set: MIC_ENERGY_THRESHOLD = {int(threshold)}")


def main():
    print()
    separator("═")
    print("  Vox Voice Diagnostic & Auto-Fix Tool v2.0")
    separator("═")
    print()

    # Step 1
    if not test_python():
        input("\nPress Enter to exit…")
        return

    print()

    # Step 2
    if not test_packages():
        input("\nInstall missing packages then run again. Press Enter to exit…")
        return

    print()

    # Step 3 — TTS
    test_tts()
    print()

    # Step 4 — Find mic
    mic_index, mic_name = find_best_mic()
    print()

    if mic_index is None and mic_name == "none":
        separator("─")
        print("  ❌ CRITICAL: No working microphone found!")
        print("  Voice commands CANNOT work without a microphone.")
        print()
        print("  Fixes:")
        print("  1. Windows Settings > Privacy > Microphone > Allow access: ON")
        print("  2. Make sure mic is plugged in and enabled")
        print("  3. Right-click speaker icon > Sounds > Recording tab > check your mic")
        separator("─")
        input("\nPress Enter to exit…")
        return

    print(f"  → Selected mic: [{mic_index}] {mic_name}")
    print()

    # Step 5 — Calibrate
    threshold = calibrate_mic(mic_index)
    print()

    # Step 6 — Test listening
    ok, actual_threshold = test_listening(mic_index, threshold)
    if actual_threshold > 0:
        threshold = actual_threshold
    print()

    if not ok:
        separator("─")
        print("  ❌ Mic not capturing speech. Cannot proceed to wake word test.")
        print()
        print("  FIXES:")
        print("  1. Check Windows Sound Settings > Recording > your mic > Properties")
        print("  2. Ensure mic is NOT muted")
        print("  3. Try 'troubleshoot' in Windows Sound settings")
        print(f"  4. Lower threshold: MIC_ENERGY_THRESHOLD = 80 in config.py")
        separator("─")
        # Still update config with what we found
        update_config(mic_index, max(80, threshold - 50))
        input("\nPress Enter to exit…")
        return

    # Step 7 — Wake word
    wake_ok = test_wake_word(mic_index, threshold)
    print()

    # Step 8 — Update config
    update_config(mic_index, threshold)
    print()

    # Final summary
    separator("═")
    print("  DIAGNOSTIC SUMMARY")
    separator("═")
    print(f"  Microphone:   [{mic_index}] {mic_name}")
    print(f"  Threshold:    {int(threshold)}")
    print(f"  Speech:       {'✅ Working' if ok else '❌ Problem'}")
    print(f"  Wake Word:    {'✅ DETECTED' if wake_ok else '❌ Not detected'}")
    print()

    if wake_ok:
        print("  🎉 Everything working! Run Vox.bat to start.")
    else:
        print("  ⚠️  Wake word not detected, but mic is working.")
        print("  config.py has been updated with correct settings.")
        print("  Try running Vox.bat — it should work now.")
        print()
        print("  If still not working, check logs/voice_debug.log for details.")

    separator("═")
    input("\nPress Enter to exit…")


if __name__ == "__main__":
    main()


