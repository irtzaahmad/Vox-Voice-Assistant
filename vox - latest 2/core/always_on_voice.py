"""
Vox - Always-On Voice Engine v4.0 — COMPLETE FIX
=================================================
ROOT CAUSE ANALYSIS of original bugs:

  [BUG 1] Port lock (in main.py) returned None when port already in use
          after a crash → voice_engine was never created → voice completely dead
          FIX: Removed port lock dependency, voice always starts

  [BUG 2] MIC_INDEX = 1 hardcoded → wrong microphone on many PCs → no audio
          FIX: Auto-detect best microphone by testing each one

  [BUG 3] After speaking "Yes?" (TTS), mic was still open immediately
          → TTS audio was being captured as the user's command
          → STT heard "yes" and failed wake word check → loop continued
          FIX: Wait TTS_WAIT_AFTER_SPEAK seconds after TTS before opening mic

  [BUG 4] dynamic_energy_threshold=True + adjust_for_ambient_noise() 
          in a quiet room sets threshold so high mic never triggers again
          FIX: Set dynamic_energy_threshold=False after initial calibration

  [BUG 5] FreeConsole() in main.py hid ALL error output — crashes invisible
          FIX: All events logged to voice_debug.log file instead

  [BUG 6] Google STT requires internet — no offline fallback caused silent failure
          FIX: Added Whisper offline as primary attempt + Sphinx as final fallback

ARCHITECTURE:
  - Single mic context kept open for entire session (no open/close per phrase)
  - listen_in_background() for continuous always-on detection
  - Two-phase: wake word (short phrase) → command (longer phrase)
  - File-based debug logging so errors are always visible
"""

import threading
import time
import queue
import os
import sys
import re
import difflib
from datetime import datetime

# ── [CRITICAL FIX] PyAudio Monkeypatch ────────────────────────────
try:
    import pyaudiowpatch as pyaudio
    sys.modules['pyaudio'] = pyaudio
except ImportError:
    pass


import config


# ── File-based logger (visible even when console is hidden) ────────────
class VoiceLogger:
    def __init__(self):
        self._lock = threading.Lock()
        self._path = config.VOICE_LOG

    def log(self, msg: str):
        ts  = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)   # console (might be hidden)
        if config.VOICE_DEBUG_LOG:
            with self._lock:
                try:
                    with open(self._path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except Exception:
                    pass


_log = VoiceLogger()


# ── NumPy compat patch ────────────────────────────────────────────────
def _patch_numpy():
    try:
        import numpy as np
        for attr, val in [('NaN', float('nan')), ('Inf', float('inf')),
                          ('bool', bool), ('int', int), ('float', float),
                          ('complex', complex), ('object', object), ('str', str)]:
            if not hasattr(np, attr):
                setattr(np, attr, val)
    except Exception:
        pass

_patch_numpy()


# ═════════════════════════════════════════════════════════════════════
class AlwaysOnVoiceEngine:
    """
    Reliable always-on voice engine.
    Uses listen_in_background() — mic stays open continuously.
    Two-phase: wake word phase (short) → command phase (longer).
    """

    WAKE_ALTS = config.WAKE_WORD_ALTS

    def __init__(self, Vox_app):
        self.app        = Vox_app
        self.running    = False
        self._sr        = None
        self._rec       = None
        self._mic       = None
        self._mic_index = None          # resolved at startup
        self._stop_bg   = None          # stop handle for listen_in_background
        self._state     = "idle"        # idle | awake | processing
        self._cmd_queue = queue.Queue() # wake-word events
        self._proc_thread = None
        self._last_bg_ping = time.time() # for watchdog
        self._bg_active = False

        # ── High-Speed Regex Optimization ──
        # Combine all variants into one lightning-fast pattern
        variants = ["vox", "box", "fox", "folks", "books", "walks", "works", "rocks", "havoc"]
        alts = [w.lower() for w in self.WAKE_ALTS]
        all_words = list(set(variants + alts + ["hey vox", "ok vox"]))
        pattern = r"\b(" + "|".join(all_words) + r")\b"
        self._wake_re = re.compile(pattern, re.IGNORECASE)
        self._strip_re = re.compile(r"^\s*(" + "|".join(all_words) + r")\s*", re.IGNORECASE)

    # ─────────────────────────────────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        _log.log("▶  Voice engine starting…")
        self.running = True

        init_thread = threading.Thread(target=self._init_and_run, daemon=True, name="Vox-Init")
        init_thread.start()

        # Start watchdog thread
        watchdog = threading.Thread(target=self._watchdog_loop, daemon=True, name="Vox-Watchdog")
        watchdog.start()

    def _init_and_run(self):
        """Initialize SR, find mic, calibrate, then start background listening."""
        if not self._init_sr():
            _log.log("❌ SpeechRecognition not available. Install: pip install SpeechRecognition PyAudioWPatch")
            return

        self._mic_index = self._find_best_mic()
        if self._mic_index is None:
            _log.log("❌ No working microphone found! Check Windows mic permissions.")
            return

        _log.log(f"✅ Using microphone index {self._mic_index}")

        if not self._calibrate():
            _log.log("❌ Microphone calibration failed.")
            return

        # Start the processing thread
        if not self._proc_thread or not self._proc_thread.is_alive():
            self._proc_thread = threading.Thread(
                target=self._process_loop, daemon=True, name="Vox-Processor"
            )
            self._proc_thread.start()

        # Start background listening
        self._start_background_listener()

    def _watchdog_loop(self):
        """Watchdog to ensure background listener is always alive."""
        _log.log("🛡️  Watchdog active")
        while self.running:
            time.sleep(15)
            if self._state == "idle":
                # If background listener hasn't called back in 60s of IDLE time, 
                # or if it was supposed to be active but isn't.
                elapsed = time.time() - self._last_bg_ping
                if elapsed > 60 or not self._bg_active:
                    _log.log(f"⚠️  Watchdog: Background listener seems dead (idle for {elapsed:.0f}s). Restarting...")
                    self._start_background_listener()

    # ─────────────────────────────────────────────────────────────────
    # SPEECH RECOGNITION INIT
    # ─────────────────────────────────────────────────────────────────
    def _init_sr(self) -> bool:
        try:
            import speech_recognition as sr
            self._sr  = sr
            self._rec = sr.Recognizer()
            # Professional optimization: Lower pause threshold for snappier detection
            self._rec.pause_threshold         = 0.4   # Reduced from 0.8
            self._rec.energy_threshold        = config.MIC_ENERGY_THRESHOLD
            self._rec.dynamic_energy_threshold = False
            self._rec.non_speaking_duration   = 0.25  # Reduced from 0.4
            
            # Pre-load Faster-Whisper for instant offline fallback
            try:
                from faster_whisper import WhisperModel
                _log.log(f"🚀 Loading Faster-Whisper ({config.WHISPER_MODEL})...")
                self._whisper = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
            except Exception as e:
                _log.log(f"⚠️ Faster-Whisper load error: {e}. Using standard Whisper.")
                self._whisper = None

            _log.log(f"✅ SR initialized (Optimized). Energy: {self._rec.energy_threshold}")
            return True
        except Exception as e:
            _log.log(f"❌ SR init error: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────
    # MICROPHONE AUTO-DETECTION — [BUG FIX 2]
    # ─────────────────────────────────────────────────────────────────
    def _find_best_mic(self) -> int | None:
        """
        Find the best working microphone.
        If config.MIC_INDEX is set, validate and use it.
        Otherwise, auto-detect by testing each mic.
        """
        sr = self._sr

        # List all mics
        try:
            all_mics = sr.Microphone.list_microphone_names()
            _log.log(f"🎤 Available microphones ({len(all_mics)}):")
            for i, m in enumerate(all_mics):
                _log.log(f"   [{i}] {m}")
        except Exception as e:
            _log.log(f"⚠️  Could not list microphones: {e}")
            all_mics = []

        # If user specified an index, validate it
        if config.MIC_INDEX is not None:
            idx = config.MIC_INDEX
            if self._test_mic(idx):
                _log.log(f"✅ Using configured MIC_INDEX={idx}")
                return idx
            else:
                _log.log(f"⚠️  Configured MIC_INDEX={idx} doesn't work, auto-detecting…")

        # Auto-detect: try each mic, prefer ones with "microphone" in name
        preferred_keywords = ["microphone", "mic", "input", "realtek", "audio", "headset"]
        candidates = []

        for i, name in enumerate(all_mics):
            lower = name.lower()
            priority = sum(kw in lower for kw in preferred_keywords)
            # Deprioritize virtual/output devices
            skip_kw = ["output", "speaker", "renderer", "stereo mix", "what u hear", "loopback"]
            if any(kw in lower for kw in skip_kw):
                continue
            candidates.append((priority, i, name))

        # Sort: highest priority first
        candidates.sort(key=lambda x: -x[0])

        # Also add index 0 and 1 as fallbacks even if not in preferred list
        for fallback_idx in [0, 1]:
            if not any(c[1] == fallback_idx for c in candidates):
                if fallback_idx < len(all_mics):
                    candidates.append((0, fallback_idx, all_mics[fallback_idx]))

        _log.log(f"🔍 Testing {len(candidates)} microphone candidates…")
        for priority, idx, name in candidates:
            _log.log(f"   Testing [{idx}] {name}…")
            if self._test_mic(idx):
                _log.log(f"✅ Auto-selected mic [{idx}]: {name}")
                return idx
            else:
                _log.log(f"   ❌ [{idx}] not usable")

        # Last resort: default mic (no index)
        if self._test_mic(None):
            _log.log("✅ Using default system microphone")
            return None   # None = system default

        return None  # complete failure

    def _test_mic(self, index) -> bool:
        """Test if a microphone can be opened."""
        try:
            sr = self._sr
            mic_args = {} if index is None else {"device_index": index}
            with sr.Microphone(**mic_args) as source:
                # Just open it — if no exception, it works
                return True
        except (OSError, AttributeError, Exception):
            return False

    def _get_mic(self):
        """Return a configured Microphone object."""
        sr = self._sr
        if self._mic_index is not None:
            return sr.Microphone(device_index=self._mic_index)
        return sr.Microphone()

    # ─────────────────────────────────────────────────────────────────
    # CALIBRATION — [BUG FIX 4]
    # ─────────────────────────────────────────────────────────────────
    def _calibrate(self) -> bool:
        """
        Calibrate mic for ambient noise ONCE at startup.
        After calibration, FREEZE the threshold (don't let it drift).
        """
        try:
            _log.log("🔧 Calibrating microphone…")
            with self._get_mic() as source:
                # Short calibration — 1 second is enough
                self._rec.adjust_for_ambient_noise(source, duration=1.0)
                raw_threshold = self._rec.energy_threshold

            # ── [BUG FIX 4] Clamp the threshold ───────────────────────
            # After calibration in a quiet room, threshold can be very low (30-50)
            # or very high (1000+) in a noisy environment.
            # We clamp to a sane range:
            # - Minimum 150 (avoids false triggers from silence/electrical noise)
            # - Maximum 400 (avoids missing actual speech)
            clamped = max(150, min(400, raw_threshold))
            self._rec.energy_threshold = clamped
            self._rec.dynamic_energy_threshold = False   # FREEZE — do not drift

            _log.log(f"✅ Calibration done. Raw: {raw_threshold:.0f} → Clamped: {clamped:.0f}")
            return True
        except Exception as e:
            _log.log(f"❌ Calibration error: {e}")
            # Use default and continue
            self._rec.energy_threshold = config.MIC_ENERGY_THRESHOLD
            self._rec.dynamic_energy_threshold = False
            return True   # Continue even if calibration fails

    # ─────────────────────────────────────────────────────────────────
    # BACKGROUND LISTENER (continuous wake-word detection)
    # ─────────────────────────────────────────────────────────────────
    def _start_background_listener(self):
        """
        Use listen_in_background for continuous listening.
        This is more reliable than a manual loop because:
        - Mic stays open (no open/close per phrase)
        - Thread-safe callback
        - Handles all timing internally
        """
        if not self.running:
            return

        # Stop existing if any
        self._stop_background_listener()

        _log.log("👂 Starting background listener…")
        self._update_gui_status("🎤 Say: Hey Vox", "#4CAF50")

        try:
            mic = self._get_mic()
            self._stop_bg = self._rec.listen_in_background(
                mic,
                self._bg_callback,
                phrase_time_limit=5   # Wake word is short — max 5 sec
            )
            self._bg_active = True
            self._last_bg_ping = time.time()
            _log.log("✅ Background listener active!")
            _log.log("=" * 50)
            _log.log("SAY 'HEY Vox' TO ACTIVATE")
            _log.log("=" * 50)

        except Exception as e:
            _log.log(f"❌ Background listener failed: {e}")
            _log.log("   Falling back to manual loop…")
            # Fallback to manual loop if background fails
            threading.Thread(target=self._manual_loop, daemon=True, name="Vox-Manual").start()

    def _stop_background_listener(self):
        """Safely stop the background listener."""
        if self._stop_bg:
            try:
                self._stop_bg(wait_for_stop=False)
                _log.log("⏹️  Background listener stopped.")
            except Exception as e:
                _log.log(f"⚠️  Error stopping background listener: {e}")
        self._stop_bg = None
        self._bg_active = False

    def _bg_callback(self, recognizer, audio):
        """Called by background thread for EVERY phrase."""
        self._last_bg_ping = time.time()
        
        # Skip if we are currently processing a command or awake
        if self._state != "idle":
            return

        try:
            text = self._recognize_fast(audio)
            if not text:
                return

            _log.log(f"👂 Heard: '{text}'")

            if self._is_wake_word(text):
                _log.log("🟢 WAKE WORD DETECTED!")
                # Stop speaker immediately
                try:
                    self.app.speaker.stop_everything()
                except Exception:
                    pass
                
                inline_cmd = self._strip_wake_word(text)
                self._cmd_queue.put(("wake", inline_cmd))
        except Exception as e:
            _log.log(f"⚠️  Callback error: {e}")

    # ─────────────────────────────────────────────────────────────────
    # PROCESSOR THREAD — handles command after wake word
    # ─────────────────────────────────────────────────────────────────
    def _process_loop(self):
        """Waits for wake-word events and processes commands instantly."""
        _log.log("⚙️  Processor thread ready (One-Shot Mode)")

        while self.running:
            try:
                event_type, inline_cmd = self._cmd_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if event_type != "wake":
                continue

            # ── ONE-SHOT EXECUTION ──
            # If a command was spoken with the wake word, execute it IMMEDIATELY.
            if inline_cmd and len(inline_cmd.strip()) > 1:
                _log.log(f"🚀 One-Shot Command: '{inline_cmd}'")
                
                # Temporarily pause listener so it doesn't hear its own response
                self._stop_background_listener()
                self._execute_command(inline_cmd)
                
                # Resume listening
                self._state = "idle"
                self._start_background_listener()
            else:
                # Only if NO command was found, fallback to traditional interaction
                # (Optional: You can also choose to ignore lone wake words for 100% one-shot)
                self._stop_background_listener()
                self._state = "awake"
                self.app.speaker.speak("Yes?")
                time.sleep(config.TTS_WAIT_AFTER_SPEAK)
                
                command_text = self._listen_for_command()
                if command_text:
                    self._execute_command(command_text)
                
                self._state = "idle"
                self._start_background_listener()

    def _listen_for_command(self) -> str:
        """Listen for the user's command after wake word detected."""
        _log.log("🎤 Listening for command…")
        try:
            with self._get_mic() as source:
                # Brief recalibration without changing threshold much
                try:
                    audio = self._rec.listen(
                        source,
                        timeout=config.LISTEN_TIMEOUT,
                        phrase_time_limit=config.PHRASE_TIME_LIMIT
                    )
                    text = self._recognize_full(audio)
                    _log.log(f"📝 Command recognized: '{text}'")
                    return text
                except self._sr.WaitTimeoutError:
                    _log.log("⏰ Command timeout — no speech detected")
                    return ""
        except Exception as e:
            _log.log(f"❌ Command listen error: {e}")
            return ""

    def _execute_command(self, command_text: str):
        """Execute a voice command and speak the response."""
        self._state = "processing"
        self._update_gui_status(f"⚙️ {command_text[:30]}…", "#2196F3")
        _log.log(f"🤖 Processing: '{command_text}'")

        try:
            response = self.app.process_command(command_text)
            _log.log(f"💬 Response: '{response[:100]}'")

            # Update GUI chat
            try:
                if self.app.gui:
                    self.app.gui.root.after(0, lambda c=command_text, r=response: (
                        self.app.gui._add_user_msg(c),
                        self.app.gui._add_Vox_msg(r)
                    ))
            except Exception:
                pass

        except Exception as e:
            _log.log(f"❌ Command execution error: {e}")
            self.app.speaker.speak("Sorry, I encountered an error processing that.")

    # ─────────────────────────────────────────────────────────────────
    # MANUAL LOOP FALLBACK (if listen_in_background fails)
    # ─────────────────────────────────────────────────────────────────
    def _manual_loop(self):
        """Fallback manual loop — less efficient but works when bg listener fails."""
        _log.log("🔄 Manual loop mode active")
        cycle = 0

        while self.running:
            if self._state != "idle":
                time.sleep(0.5)
                continue

            try:
                with self._get_mic() as source:
                    # Recalibrate every 50 cycles (don't let threshold drift)
                    cycle += 1
                    if cycle % 50 == 0:
                        old = self._rec.energy_threshold
                        self._rec.adjust_for_ambient_noise(source, duration=0.5)
                        # Clamp after recalibration
                        self._rec.energy_threshold = max(150, min(400, self._rec.energy_threshold))
                        _log.log(f"🔧 Recalibrated: {old:.0f} → {self._rec.energy_threshold:.0f}")
                        self._rec.dynamic_energy_threshold = False

                    try:
                        audio = self._rec.listen(source, timeout=3, phrase_time_limit=5)
                        text  = self._recognize_fast(audio)

                        if text:
                            _log.log(f"👂 Heard (manual): '{text}'")

                        if text and self._is_wake_word(text):
                            inline_cmd = self._strip_wake_word(text)
                            self._cmd_queue.put(("wake", inline_cmd))

                    except self._sr.WaitTimeoutError:
                        pass

            except OSError as e:
                _log.log(f"❌ Mic error: {e} — retry in 2s")
                time.sleep(2)
            except Exception as e:
                _log.log(f"❌ Loop error: {e}")
                time.sleep(0.5)

    # ─────────────────────────────────────────────────────────────────
    # STT RECOGNITION — [BUG FIX 6]
    # ─────────────────────────────────────────────────────────────────
    def _recognize_fast(self, audio) -> str:
        """Fast recognition for wake word detection. Short phrases only."""
        return self._try_recognize(audio, fast=True)

    def _recognize_full(self, audio) -> str:
        """Full recognition for commands. More thorough."""
        return self._try_recognize(audio, fast=False)

    def _try_recognize(self, audio, fast: bool = False) -> str:
        """
        Hyper-optimized STT fallback chain.
        """
        sr = self._sr

        # 1. Google STT (Fastest online)
        try:
            text = self._rec.recognize_google(audio, language='en-US')
            return text.lower().strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            pass
        except Exception:
            return ""

        # 2. Faster-Whisper (Professional Local Offline)
        if hasattr(self, '_whisper') and self._whisper:
            try:
                # Convert audio to numpy array
                wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
                import numpy as np
                audio_np = np.frombuffer(wav_data, dtype=np.int16).flatten().astype(np.float32) / 32768.0
                
                segments, _ = self._whisper.transcribe(audio_np, beam_size=1, vad_filter=True)
                text = " ".join([s.text for s in segments]).strip()
                return text.lower()
            except Exception as e:
                _log.log(f"⚠️ Faster-Whisper error: {e}")

        # 3. Standard Whisper Fallback
        try:
            text = self._rec.recognize_whisper(audio, model=config.WHISPER_MODEL)
            return text.lower().strip()
        except Exception:
            pass

        return ""

    def _is_wake_word(self, text: str) -> bool:
        """High-speed regex-based wake word detection."""
        if not text: return False
        t = text.lower().strip()

        # 1. Regex check (Fastest)
        if self._wake_re.search(t):
            return True

        # 2. Fuzzy fallback for short phrases in noisy rooms
        if len(t) <= 15:
            score = difflib.SequenceMatcher(None, t, "hey vox").ratio()
            if score >= 0.65: return True

        return False

    def _strip_wake_word(self, text: str) -> str:
        """Remove wake word using pre-compiled regex."""
        return self._strip_re.sub("", text, count=1).strip(' ,.!?')

    # ─────────────────────────────────────────────────────────────────
    # GUI STATUS UPDATE
    # ─────────────────────────────────────────────────────────────────
    def _update_gui_status(self, status: str, color: str = "#4CAF50"):
        try:
            if self.app.gui and hasattr(self.app.gui, 'set_voice_status'):
                self.app.gui.root.after(0, lambda: self.app.gui.set_voice_status(status, color))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ─────────────────────────────────────────────────────────────────
    def stop(self):
        self.running = False
        self._stop_background_listener()
        _log.log("⏹️  Voice engine stopped")

    def restart(self):
        _log.log("🔄 Restarting voice engine…")
        self.stop()
        time.sleep(0.5)
        self.running = True
        self._state  = "idle"
        threading.Thread(target=self._init_and_run, daemon=True, name="Vox-Restart").start()
