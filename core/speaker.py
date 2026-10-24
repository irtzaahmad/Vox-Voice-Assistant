import asyncio
import threading
import queue
import time
import os
import sys
import tempfile
import subprocess

import config


class VoxSpeaker:
    def __init__(self):
        self._queue = queue.Queue()
        self._running = True
        self._speaking = False
        self._lock = threading.Lock()
        self._current_proc = None
        self._last_speak_end = 0.0
        self._thread = threading.Thread(target=self._worker, daemon=True, name="Vox-TTS")
        self._thread.start()
        print("Speaker (Edge TTS) initialized")

    @property
    def is_speaking(self):
        with self._lock:
            return self._speaking

    @property
    def recently_spoke(self):
        with self._lock:
            if self._speaking:
                return True
            return time.time() - self._last_speak_end < 1.5

    def _worker(self):
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if text is None:
                    break

                with self._lock:
                    self._speaking = True

                try:
                    asyncio.run(self._speak_async(text))
                except Exception as e:
                    print(f"[Speaker] Error: {e}")

                with self._lock:
                    self._speaking = False
                    self._last_speak_end = time.time()
                self._queue.task_done()
            except queue.Empty:
                continue

    async def _speak_async(self, text: str):
        import edge_tts

        voice = config.EDGE_TTS_VOICE
        communicate = edge_tts.Communicate(text, voice)

        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            tmp = f.name

        try:
            await communicate.save(tmp)

            played = False

            # 1. Try ffplay (part of ffmpeg) — store proc for kill
            if not played:
                try:
                    proc = await asyncio.create_subprocess_exec(
                        'ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', tmp,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    with self._lock:
                        self._current_proc = proc
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=30)
                    except (FileNotFoundError, asyncio.TimeoutError):
                        pass
                    finally:
                        with self._lock:
                            self._current_proc = None
                    played = True
                except FileNotFoundError:
                    pass

            # 2. Try pygame mixer — poll speaking flag for interrupt
            if not played:
                try:
                    import pygame
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(tmp)
                    pygame.mixer.music.play()
                    while self._speaking and pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                    played = True
                except Exception:
                    pass

            # 3. Windows MCI — non-blocking play, poll mode for interrupt
            if not played and sys.platform == 'win32':
                try:
                    import ctypes
                    mci = ctypes.windll.winmm
                    mci.mciSendStringW(f'open "{tmp}" type mpegvideo alias vox_tts', None, 0, 0)
                    mci.mciSendStringW('play vox_tts', None, 0, 0)
                    buf = ctypes.create_unicode_buffer(128)
                    while self._speaking:
                        mci.mciSendStringW('status vox_tts mode', buf, 128, 0)
                        if buf.value != 'playing':
                            break
                        time.sleep(0.05)
                    mci.mciSendStringW('close vox_tts', None, 0, 0)
                    played = True
                except Exception:
                    pass

            if not played:
                print(f"[Speaker] No audio player available. Text: {text[:50]}")
                print("[Speaker] Install ffmpeg or pygame for TTS playback.")

        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

    def speak(self, text: str):
        if text and isinstance(text, str) and text.strip():
            print(f"[Vox] {text}")
            self._queue.put(text.strip())

    def speak_and_wait(self, text: str, extra_wait: float = 0.3):
        if not text or not text.strip():
            return
        self.speak(text)
        self._queue.join()
        time.sleep(extra_wait)

    def wait_until_done(self, timeout: float = 10.0):
        try:
            self._queue.join()
        except Exception:
            pass

    def stop_everything(self):
        with self._lock:
            if self._current_proc:
                try:
                    self._current_proc.kill()
                except Exception:
                    pass
                self._current_proc = None
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
        if sys.platform == 'win32':
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW('close vox_tts', None, 0, 0)
            except Exception:
                pass
        with self._lock:
            self._speaking = False
            self._last_speak_end = time.time()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        print("Speech queue cleared")

    def stop(self):
        self._running = False
        self._queue.put(None)


_speaker_instance = None
_speaker_lock = threading.Lock()


def get_speaker() -> VoxSpeaker:
    global _speaker_instance
    with _speaker_lock:
        if _speaker_instance is None:
            _speaker_instance = VoxSpeaker()
    return _speaker_instance
