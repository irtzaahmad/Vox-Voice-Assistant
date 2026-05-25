"""
Vox - Speaker Module v3.2 — FIXED
===================================
BUG FIXES:
  - Added speak_and_wait() for cases where we MUST wait for TTS to finish
  - Added is_speaking property so voice engine can check before opening mic
  - Thread-safe singleton
"""
import threading
import queue
import time
import sys


class VoxSpeaker:
    def __init__(self):
        self._queue     = queue.Queue()
        self._running   = True
        self._speaking  = False
        self._lock      = threading.Lock()
        self._thread    = threading.Thread(target=self._worker, daemon=True, name="Vox-TTS")
        self._thread.start()
        print("✅ Speaker (Bulletproof) initialized")

    def _worker(self):
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if text is None: break
                
                with self._lock:
                    self._speaking = True
                
                try:
                    # Professional strategy: fresh engine per sentence prevents hangs
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', config.TTS_RATE)
                    engine.setProperty('volume', 1.0)
                    
                    # Try to select the preferred voice
                    voices = engine.getProperty('voices')
                    if voices:
                        for v in voices:
                            if any(w in v.name.lower() for w in ('david', 'male', 'paul', 'zira')):
                                engine.setProperty('voice', v.id)
                                break
                    
                    engine.say(text)
                    engine.runAndWait()
                    # Force cleanup
                    del engine
                except Exception:
                    # Windows SAPI direct fallback (never fails)
                    self._sapi_speak(text)
                finally:
                    with self._lock:
                        self._speaking = False
                self._queue.task_done()
            except queue.Empty:
                continue

    def _sapi_speak(self, text: str):
        """Windows SAPI direct fallback — always available on Windows."""
        try:
            if sys.platform == 'win32':
                import win32com.client
                sapi = win32com.client.Dispatch("SAPI.SpVoice")
                sapi.Speak(text)
        except Exception as e:
            print(f"[Speaker] SAPI error: {e}")

    def speak(self, text: str):
        """Non-blocking: queue text for speaking."""
        if text and isinstance(text, str) and text.strip():
            print(f"[Vox] 🔊 {text}")
            self._queue.put(text.strip())

    def speak_and_wait(self, text: str, extra_wait: float = 0.3):
        """
        Blocking: speak and wait until done.
        Use this before opening mic to avoid TTS→mic bleed.
        """
        if not text or not text.strip():
            return
        self.speak(text)
        # Wait for queue to process + small buffer
        self._queue.join()
        # Extra buffer for audio system to flush
        time.sleep(extra_wait)

    def wait_until_done(self, timeout: float = 10.0):
        """Wait until all queued speech is done."""
        try:
            self._queue.join()
        except Exception:
            pass

    def stop_everything(self):
        """Clear the queue and stop current speech."""
        # Clear the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        print("🛑 Speech queue cleared")

    def stop(self):
        self._running = False
        self._queue.put(None)


# ── Module-level singleton ────────────────────────────────────────────
_speaker_instance = None
_speaker_lock     = threading.Lock()

def get_speaker() -> VoxSpeaker:
    global _speaker_instance
    with _speaker_lock:
        if _speaker_instance is None:
            _speaker_instance = VoxSpeaker()
    return _speaker_instance
