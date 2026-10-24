"""
Vox — Always-On Voice Engine v5.1
Architecture:  PyAudio → Groq Whisper API → AI Brain → Edge TTS → local speaker
"""

import threading
import time
import queue
import os
import sys
import re
import difflib
from datetime import datetime

try:
    import pyaudiowpatch as pyaudio
    sys.modules['pyaudio'] = pyaudio
except ImportError:
    pass

import config


class VoiceLogger:
    def __init__(self):
        self._lock = threading.Lock()
        self._path = config.VOICE_LOG

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        if config.VOICE_DEBUG_LOG:
            with self._lock:
                try:
                    with open(self._path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                except Exception:
                    pass


_log = VoiceLogger()


class AlwaysOnVoiceEngine:
    WAKE_ALTS = config.WAKE_WORD_ALTS

    def __init__(self, Vox_app):
        self.app = Vox_app
        self.running = False
        self._state = "idle"
        self._cmd_queue = queue.Queue()
        self._proc_thread = None
        self._last_bg_ping = time.time()
        self._bg_active = False

        self._conversation_timeout = 8
        self._last_activity = time.time()

        self._groq_api_key = None
        self._groq_whisper_model = None
        self._sr = None
        self._rec = None
        self._mic_index = None
        self._stop_bg = None

        variants = ["vox", "box", "book", "books", "bucks", "fox"]
        alts = [w.lower() for w in self.WAKE_ALTS]
        all_words = list(set(variants + alts + ["hey vox", "ok vox"]))
        all_words = [w for w in all_words if w]
        all_words.sort(key=len, reverse=True)

        pattern = r"\b(" + "|".join(re.escape(w) for w in all_words if w.isascii()) + r")\b"
        self._wake_re = re.compile(pattern, re.IGNORECASE)
        ascii_words = [w for w in all_words if w.isascii()]
        self._strip_re = re.compile(r"^\s*(" + "|".join(re.escape(w) for w in ascii_words) + r")\s*", re.IGNORECASE)

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────

    def start(self):
        if self.running:
            return
        _log.log("Voice engine starting…")
        self.running = True

        self._init_groq_stt()

        _log.log("Local audio mode")
        threading.Thread(target=self._init_and_run_local, daemon=True, name="Vox-Init").start()

        wd = threading.Thread(target=self._watchdog_loop, daemon=True, name="Vox-Watchdog")
        wd.start()

    def stop(self):
        self.running = False
        self._stop_background_listener()
        _log.log("Voice engine stopped")

    def restart(self):
        _log.log("Restarting voice engine…")
        self.stop()
        time.sleep(0.5)
        self.running = True
        self._state = "idle"
        self._init_groq_stt()
        threading.Thread(target=self._init_and_run_local, daemon=True).start()

    def listen_for_command(self) -> str:
        _log.log("Listening for command…")
        try:
            with self._get_mic() as source:
                try:
                    audio = self._rec.listen(
                        source,
                        timeout=config.LISTEN_TIMEOUT,
                        phrase_time_limit=config.PHRASE_TIME_LIMIT
                    )
                    text = self._recognize_full(audio)
                    _log.log(f"Command recognized: '{text}'")
                    return text
                except self._sr.WaitTimeoutError:
                    _log.log("Command timeout — no speech detected")
                    return ""
        except Exception as e:
            _log.log(f"Command listen error: {e}")
            return ""

    # ─────────────────────────────────────────────────────────────────
    # GROQ STT INIT
    # ─────────────────────────────────────────────────────────────────

    def _init_groq_stt(self):
        self._groq_api_key = config.GROQ_API_KEY
        self._groq_whisper_model = config.GROQ_WHISPER_MODEL
        if self._groq_api_key:
            _log.log(f"Groq Whisper API configured (model: {self._groq_whisper_model})")
        else:
            _log.log("No Groq API key — STT will use Google fallback only")

    def _transcribe_groq(self, wav_bytes: bytes) -> str:
        if not self._groq_api_key:
            return ""
        try:
            import requests
            resp = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._groq_api_key}"},
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                data={
                    "model": self._groq_whisper_model,
                    "language": "en",
                    "response_format": "json"
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json().get("text", "").strip()
            else:
                _log.log(f"Groq Whisper error: {resp.status_code} {resp.text}")
                return ""
        except Exception as e:
            _log.log(f"Groq Whisper exception: {e}")
            return ""

    # ─────────────────────────────────────────────────────────────────
    # LOCAL AUDIO MODE (PyAudio + SpeechRecognition)
    # ─────────────────────────────────────────────────────────────────

    def _init_and_run_local(self):
        if not self._init_sr():
            _log.log("SpeechRecognition not available. Install: pip install SpeechRecognition PyAudioWPatch")
            return

        self._mic_index = self._find_best_mic()
        if self._mic_index is None:
            _log.log("No working microphone found! Check Windows mic permissions.")
            return

        _log.log(f"Using microphone index {self._mic_index}")

        if not self._calibrate():
            _log.log("Microphone calibration failed.")
            return

        if not self._proc_thread or not self._proc_thread.is_alive():
            self._proc_thread = threading.Thread(
                target=self._process_loop, daemon=True, name="Vox-Processor"
            )
            self._proc_thread.start()

        self._start_background_listener()

    def _watchdog_loop(self):
        _log.log("Watchdog active")
        while self.running:
            time.sleep(15)
            if self._state == "idle" and self._sr is not None:
                elapsed = time.time() - self._last_bg_ping
                if elapsed > 60 or not self._bg_active:
                    _log.log(f"Watchdog: Background listener seems dead (idle for {elapsed:.0f}s). Restarting…")
                    self._start_background_listener()

    # ── SpeechRecognition Init ──────────────────────────────────────

    def _init_sr(self) -> bool:
        try:
            import speech_recognition as sr
            self._sr = sr
            self._rec = sr.Recognizer()
            self._rec.pause_threshold = 0.4
            self._rec.energy_threshold = config.MIC_ENERGY_THRESHOLD
            self._rec.dynamic_energy_threshold = False
            self._rec.non_speaking_duration = 0.25

            _log.log(f"SR initialized. Energy: {self._rec.energy_threshold}")
            return True
        except Exception as e:
            _log.log(f"SR init error: {e}")
            return False

    # ── Microphone detection ─────────────────────────────────────────

    def _find_best_mic(self) -> int | None:
        sr = self._sr

        try:
            all_mics = sr.Microphone.list_microphone_names()
            _log.log(f"Available microphones ({len(all_mics)}):")
            for i, m in enumerate(all_mics):
                _log.log(f"   [{i}] {m}")
        except Exception as e:
            _log.log(f"Could not list microphones: {e}")
            all_mics = []

        if config.MIC_INDEX is not None:
            idx = config.MIC_INDEX
            if self._test_mic(idx):
                _log.log(f"Using configured MIC_INDEX={idx}")
                return idx
            else:
                _log.log(f"Configured MIC_INDEX={idx} doesn't work, auto-detecting…")

        preferred_keywords = ["microphone", "mic", "input", "realtek", "audio", "headset"]
        candidates = []

        for i, name in enumerate(all_mics):
            lower = name.lower()
            priority = sum(kw in lower for kw in preferred_keywords)
            skip_kw = ["output", "speaker", "renderer", "stereo mix", "what u hear", "loopback"]
            if any(kw in lower for kw in skip_kw):
                continue
            candidates.append((priority, i, name))

        candidates.sort(key=lambda x: -x[0])

        for fallback_idx in [0, 1]:
            if not any(c[1] == fallback_idx for c in candidates):
                if fallback_idx < len(all_mics):
                    candidates.append((0, fallback_idx, all_mics[fallback_idx]))

        _log.log(f"Testing {len(candidates)} microphone candidates…")
        for priority, idx, name in candidates:
            _log.log(f"   Testing [{idx}] {name}…")
            if self._test_mic(idx):
                _log.log(f"Auto-selected mic [{idx}]: {name}")
                return idx
            else:
                _log.log(f"   [{idx}] not usable")

        if self._test_mic(None):
            _log.log("Using default system microphone")
            return None

        return None

    def _test_mic(self, index) -> bool:
        try:
            sr = self._sr
            mic_args = {} if index is None else {"device_index": index}
            with sr.Microphone(**mic_args) as source:
                return True
        except (OSError, AttributeError, Exception):
            return False

    def _get_mic(self):
        sr = self._sr
        if self._mic_index is not None:
            return sr.Microphone(device_index=self._mic_index)
        return sr.Microphone()

    # ── Calibration ──────────────────────────────────────────────────

    def _calibrate(self) -> bool:
        try:
            _log.log("Calibrating microphone…")
            with self._get_mic() as source:
                self._rec.adjust_for_ambient_noise(source, duration=1.0)
                raw_threshold = self._rec.energy_threshold

            clamped = max(config.MIC_ENERGY_MIN_CLAMP, min(config.MIC_ENERGY_MAX_CLAMP, raw_threshold))
            self._rec.energy_threshold = clamped
            self._rec.dynamic_energy_threshold = False

            _log.log(f"Calibration done. Raw: {raw_threshold:.0f} -> Clamped: {clamped:.0f}")
            return True
        except Exception as e:
            _log.log(f"Calibration error: {e}")
            self._rec.energy_threshold = config.MIC_ENERGY_THRESHOLD
            self._rec.dynamic_energy_threshold = False
            return True

    # ── Background listener (local mode) ──────────────────────────────

    def _start_background_listener(self):
        if not self.running:
            return

        self._stop_background_listener()

        _log.log("Starting background listener…")
        self._update_gui_status("Say: Hey Vox", "#4CAF50")

        try:
            mic = self._get_mic()
            self._stop_bg = self._rec.listen_in_background(
                mic,
                self._bg_callback,
                phrase_time_limit=5
            )
            self._bg_active = True
            self._last_bg_ping = time.time()
            _log.log("Background listener active!")
            _log.log("SAY 'HEY Vox' TO ACTIVATE")
        except Exception as e:
            _log.log(f"Background listener failed: {e}")
            _log.log("Falling back to manual loop…")
            threading.Thread(target=self._manual_loop, daemon=True, name="Vox-Manual").start()

    def _stop_background_listener(self):
        if self._stop_bg:
            try:
                self._stop_bg(wait_for_stop=False)
                _log.log("Background listener stopped.")
            except Exception as e:
                _log.log(f"Error stopping background listener: {e}")
        self._stop_bg = None
        self._bg_active = False

    def _bg_callback(self, recognizer, audio):
        self._last_bg_ping = time.time()

        try:
            text = self._recognize_fast(audio)
            if not text:
                return

            _log.log(f"Heard: '{text}'")

            # Barge-in: stop phrase during TTS playback or echo window
            if self.app.speaker.recently_spoke:
                stop_phrases = ("stop", "stop talking", "shut up", "be quiet",
                                "silence", "enough", "that's enough", "stop it",
                                "shut your mouth", "cut it out")
                t = text.lower().strip().strip(' .,!?')
                if any(p in t for p in stop_phrases):
                    _log.log("BARGE-IN: Stop talking detected")
                    self.app.speaker.stop_everything()
                    self._state = "idle"
                    self._update_gui_status("Say: Hey Vox", "#4CAF50")
                    return
                return  # ignore all other audio while TTS is playing

            state = self._state
            if state == "processing":
                return

            if state == "idle":
                if self._is_wake_word(text):
                    _log.log("WAKE WORD DETECTED!")
                    try:
                        self.app.speaker.stop_everything()
                    except Exception:
                        pass
                    inline_cmd = self._strip_wake_word(text)
                    self._cmd_queue.put(("wake", inline_cmd))

            elif state == "listening":
                _log.log("Conversation follow-up detected")
                self._cmd_queue.put(("command", text))

        except Exception as e:
            _log.log(f"Callback error: {e}")

    # ── STT (Whisper primary, Google fallback) ──────────────────────

    def _recognize_fast(self, audio) -> str:
        return self._try_recognize(audio, fast=True)

    def _recognize_full(self, audio) -> str:
        return self._try_recognize(audio, fast=False)

    def _denoise_wav(self, wav_data: bytes) -> bytes:
        try:
            import io
            import wave
            import numpy as np
            import noisereduce as nr

            with io.BytesIO(wav_data) as buf:
                with wave.open(buf, 'rb') as w:
                    ch = w.getnchannels()
                    sw = w.getsampwidth()
                    fr = w.getframerate()
                    frames = w.readframes(w.getnframes())

            if len(frames) < 1600:
                return wav_data

            raw = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            denoised = nr.reduce_noise(y=raw, sr=fr, stationary=True, prop_decrease=0.7)
            clean = (denoised * 32768.0).astype(np.int16).tobytes()

            with io.BytesIO() as out:
                with wave.open(out, 'wb') as w:
                    w.setnchannels(ch)
                    w.setsampwidth(sw)
                    w.setframerate(fr)
                    w.writeframes(clean)
                return out.getvalue()
        except Exception:
            return wav_data

    def _try_recognize(self, audio, fast: bool = False) -> str:
        # 1. Groq Whisper API (cloud, fast, English) — with noise reduction
        if self._groq_api_key:
            try:
                wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
                wav_data = self._denoise_wav(wav_data)
                text = self._transcribe_groq(wav_data)
                if text:
                    return text.lower()
            except Exception as e:
                _log.log(f"Groq Whisper error: {e}")

        # 2. Google STT fallback (English online) — with noise reduction
        sr = self._sr
        try:
            wav_data = audio.get_wav_data(convert_rate=16000, convert_width=2)
            wav_data = self._denoise_wav(wav_data)
            import speech_recognition as sr_mod
            clean_audio = sr_mod.AudioData(wav_data, 16000, 2)
            text = self._rec.recognize_google(clean_audio, language='en-US')
            return text.lower().strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            pass
        except Exception:
            return ""

        return ""

    # ── Wake word detection ─────────────────────────────────────────

    def _is_wake_word(self, text: str) -> bool:
        if not text:
            return False
        t = text.lower().strip()

        _log.log(f"WW check: '{t}'")

        # If text is purely non-Latin, reject — no Urdu support
        has_latin = any(c.isascii() and c.isalpha() for c in t)
        if not has_latin:
            return False

        # 1. English regex match
        if self._wake_re.search(t):
            _log.log("WW: regex match")
            return True

        # 2. Check each word individually for wake-like words
        for word in t.split():
            w = word.strip(' .,!?')
            if w in ("vox", "box", "voc", "book", "books", "bucks", "fox"):
                _log.log(f"WW: single word match ({w})")
                return True

        # 4. Fuzzy match for short English phrases
        if len(t) <= 25:
            score = difflib.SequenceMatcher(None, t, "hey vox").ratio()
            if score >= 0.5:
                _log.log(f"WW: fuzzy match ({score:.2f})")
                return True

        return False

    def _is_goodbye(self, text: str) -> bool:
        goodbye = {"bye", "goodbye", "stop", "exit", "quit", "that's all",
                    "that is all", "nothing", "no thanks", "bye bye",
                    "see you", "good night", "talk to you later", "enough"}
        t = text.lower().strip().strip(' .,!?')
        return t in goodbye or any(t.startswith(w) for w in goodbye)

    def _strip_wake_word(self, text: str) -> str:
        t = self._strip_re.sub("", text, count=1).strip(' ,.!?')
        return t.strip(' ,.!?')

    # ── Processor loop (local mode) ─────────────────────────────────

    def _process_loop(self):
        _log.log("Processor thread ready (Conversation Mode)")

        while self.running:
            try:
                event_type, cmd = self._cmd_queue.get(timeout=0.5)
            except queue.Empty:
                if self._state == "listening" and time.time() - self._last_activity > self._conversation_timeout:
                    _log.log("Conversation timeout — returning to idle")
                    self._state = "idle"
                    self._update_gui_status("Say: Hey Vox", "#4CAF50")
                continue

            if event_type == "wake":
                if cmd and len(cmd.strip()) > 1:
                    _log.log(f"One-Shot Command: '{cmd}'")
                    self._stop_background_listener()
                    self._execute_command(cmd)
                    self._enter_listening_state()
                    self._start_background_listener()
                else:
                    self._stop_background_listener()
                    self._state = "awake"
                    self.app.speaker.speak("Yes?")
                    time.sleep(config.TTS_WAIT_AFTER_SPEAK)
                    command_text = self.listen_for_command()
                    if command_text and not self._is_goodbye(command_text):
                        self._execute_command(command_text)
                        self._enter_listening_state()
                    else:
                        self._state = "idle"
                    self._start_background_listener()

            elif event_type == "command" and self._state == "listening":
                if self._is_goodbye(cmd):
                    _log.log("Goodbye detected — ending conversation")
                    self.app.speaker.speak("Goodbye!")
                    self._state = "idle"
                    self._update_gui_status("Say: Hey Vox", "#4CAF50")
                else:
                    self._execute_command(cmd)
                    self._enter_listening_state()

    def _enter_listening_state(self):
        self._state = "listening"
        self._last_activity = time.time()
        self._update_gui_status("Listening... (8s)", "#FF9800")
        _log.log("Entered conversation mode — listening for follow-up (8s timeout)")

    def _execute_command(self, command_text: str):
        self._state = "processing"
        self._update_gui_status(f"Processing: {command_text[:30]}…", "#2196F3")
        _log.log(f"Processing: '{command_text}'")

        try:
            response = self.app.process_command(command_text)
            _log.log(f"Response: '{response[:100]}'")

            try:
                if self.app.gui:
                    self.app.gui.root.after(0, lambda c=command_text, r=response: (
                        self.app.gui._add_user_msg(c),
                        self.app.gui._add_Vox_msg(r)
                    ))
            except Exception:
                pass

        except Exception as e:
            _log.log(f"Command execution error: {e}")
            self.app.speaker.speak("Sorry, I encountered an error processing that.")

    # ── Manual loop fallback ────────────────────────────────────────

    def _manual_loop(self):
        _log.log("Manual loop mode active")
        cycle = 0

        while self.running:
            if self._state != "idle":
                time.sleep(0.5)
                continue

            try:
                with self._get_mic() as source:
                    cycle += 1
                    if cycle % 50 == 0:
                        old = self._rec.energy_threshold
                        self._rec.adjust_for_ambient_noise(source, duration=0.5)
                        self._rec.energy_threshold = max(config.MIC_ENERGY_MIN_CLAMP, min(config.MIC_ENERGY_MAX_CLAMP, self._rec.energy_threshold))
                        _log.log(f"Recalibrated: {old:.0f} -> {self._rec.energy_threshold:.0f}")
                        self._rec.dynamic_energy_threshold = False

                    try:
                        audio = self._rec.listen(source, timeout=3, phrase_time_limit=5)
                        text = self._recognize_fast(audio)

                        if text:
                            _log.log(f"Heard (manual): '{text}'")

                        if text and self._is_wake_word(text):
                            inline_cmd = self._strip_wake_word(text)
                            self._cmd_queue.put(("wake", inline_cmd))

                    except self._sr.WaitTimeoutError:
                        pass

            except OSError as e:
                _log.log(f"Mic error: {e} — retry in 2s")
                time.sleep(2)
            except Exception as e:
                _log.log(f"Loop error: {e}")
                time.sleep(0.5)

    # ── GUI status ──────────────────────────────────────────────────

    def _update_gui_status(self, status: str, color: str = "#4CAF50"):
        try:
            if self.app.gui and hasattr(self.app.gui, 'set_voice_status'):
                self.app.gui.root.after(0, lambda: self.app.gui.set_voice_status(status, color))
        except Exception:
            pass
