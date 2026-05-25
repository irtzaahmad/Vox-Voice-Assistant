"""
Vox - Voice Recognition / Enrollment Module (FIXED v3.1)
=========================================================
FIX: NumPy 2.0 compatibility — np.NaN, np.bool, np.int removed in NumPy 2.0
FIX: Voice print enrollment no longer crashes
FIX: scipy/librosa version compatibility patches applied
"""

import os
import sys
import numpy as np
import threading

# ── [CRITICAL FIX] PyAudio Monkeypatch ────────────────────────────
try:
    import pyaudiowpatch as pyaudio
    sys.modules['pyaudio'] = pyaudio
except ImportError:
    pass

import config


# ── NumPy 2.0 compatibility patch ─────────────────────────────────────
# Many audio/ML libraries still use removed np.NaN, np.bool etc.
def _apply_numpy_compat_patches():
    """Patch numpy to restore removed aliases needed by older libraries."""
    patches = {
        'NaN': float('nan'),
        'Inf': float('inf'),
        'bool': bool,
        'int': int,
        'float': float,
        'complex': complex,
        'object': object,
        'str': str,
    }
    for attr, val in patches.items():
        if not hasattr(np, attr):
            setattr(np, attr, val)

_apply_numpy_compat_patches()


class VoiceRecognitionModule:
    """
    Voice print enrollment and verification.
    Records audio samples, extracts MFCC features, stores voice print.
    """

    def __init__(self, voice_prints_dir: str = None):
        self.voice_prints_dir = voice_prints_dir or config.VOICE_PRINTS_DIR
        os.makedirs(self.voice_prints_dir, exist_ok=True)
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────
    def _safe_import_audio_libs(self):
        """
        Import audio processing libs with compat patches applied.
        Returns (librosa, soundfile) or (None, None) on failure.
        """
        _apply_numpy_compat_patches()   # re-apply before import

        librosa = None
        soundfile = None

        try:
            # patch before librosa touches numpy internals
            import numpy as _np
            _apply_numpy_compat_patches()
            import librosa as _librosa
            librosa = _librosa
        except ImportError:
            print("[VoiceRec] librosa not installed: pip install librosa")
        except AttributeError as e:
            print(f"[VoiceRec] librosa numpy compat error: {e}")
            print("[VoiceRec] Fix: pip install 'numpy<2.0' or 'librosa>=0.10.2'")

        try:
            import soundfile as _sf
            soundfile = _sf
        except ImportError:
            pass   # optional

        return librosa, soundfile

    # ─────────────────────────────────────────────────────────────────
    def enroll_user(self, user_id: int, username: str,
                    progress_callback=None) -> tuple[bool, str]:
        """
        Record voice samples and save voice print for a user.
        Returns (success: bool, message: str)
        """
        _apply_numpy_compat_patches()

        try:
            import speech_recognition as sr
        except ImportError:
            return False, "speech_recognition not installed"

        librosa, _ = self._safe_import_audio_libs()

        rec     = sr.Recognizer()
        mic     = sr.Microphone(device_index=config.MIC_INDEX)
        samples = []

        phrases = [
            "My name is {name} and I am the authorized user of Vox".format(name=username),
            "Hey Vox, open YouTube and play some music",
            "Good morning Vox, what is the weather today",
        ]

        for i, phrase in enumerate(phrases, 1):
            if progress_callback:
                progress_callback(f"🎤 Sample {i}/3 — Please say:\n\"{phrase}\"")

            time_module = __import__('time')
            time_module.sleep(0.8)

            try:
                with mic as source:
                    rec.adjust_for_ambient_noise(source, duration=0.5)
                    audio = rec.listen(source, timeout=10, phrase_time_limit=8)

                # convert to numpy array (safe for NumPy 2.0)
                raw = audio.get_raw_data(convert_rate=22050, convert_width=2)
                audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                audio_np /= 32768.0   # normalize to [-1, 1]
                samples.append(audio_np)

                if progress_callback:
                    progress_callback(f"✅ Sample {i}/3 recorded")

            except sr.WaitTimeoutError:
                return False, f"No audio detected for sample {i}. Please try again."
            except Exception as e:
                return False, f"Recording error on sample {i}: {e}"

        # ── Extract and save voice print ───────────────────────────────
        try:
            voice_print = self._extract_voice_print(samples, librosa)
            save_path   = os.path.join(self.voice_prints_dir, f"user_{user_id}.npy")
            np.save(save_path, voice_print)
            return True, f"✅ Voice print enrolled for {username}!"
        except Exception as e:
            return False, f"Voice print save error: {e}"

    # ─────────────────────────────────────────────────────────────────
    def _extract_voice_print(self, samples: list, librosa=None) -> np.ndarray:
        """
        Extract MFCC features from audio samples.
        Falls back to simple spectral features if librosa unavailable.
        """
        all_features = []

        for audio_np in samples:
            if librosa is not None:
                try:
                    _apply_numpy_compat_patches()
                    mfccs = librosa.feature.mfcc(
                        y=audio_np, sr=22050, n_mfcc=40
                    )
                    features = np.mean(mfccs, axis=1)   # shape: (40,)
                    all_features.append(features)
                    continue
                except Exception as e:
                    print(f"[VoiceRec] MFCC error: {e}, using fallback")

            # ── Simple FFT fallback (no librosa needed) ────────────────
            fft = np.abs(np.fft.rfft(audio_np, n=2048))
            # take first 40 bins as "voice print"
            features = fft[:40] / (np.max(fft) + 1e-9)
            all_features.append(features)

        # average across samples
        voice_print = np.mean(np.array(all_features), axis=0)
        return voice_print

    # ─────────────────────────────────────────────────────────────────
    def verify_user(self, audio_data, user_id: int) -> tuple[bool, float]:
        """
        Verify if audio matches enrolled voice print.
        Returns (match: bool, confidence: float 0-1)
        """
        _apply_numpy_compat_patches()
        save_path = os.path.join(self.voice_prints_dir, f"user_{user_id}.npy")

        if not os.path.exists(save_path):
            return False, 0.0

        try:
            stored_print = np.load(save_path)
            import speech_recognition as sr
            librosa, _ = self._safe_import_audio_libs()

            raw = audio_data.get_raw_data(convert_rate=22050, convert_width=2)
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            audio_np /= 32768.0

            current_print = self._extract_voice_print([audio_np], librosa)

            # cosine similarity
            dot    = np.dot(stored_print, current_print)
            norms  = np.linalg.norm(stored_print) * np.linalg.norm(current_print)
            sim    = float(dot / (norms + 1e-9))
            sim    = max(0.0, min(1.0, sim))   # clamp to [0,1]

            match  = sim >= config.VOICE_RECOGNITION_THRESHOLD
            return match, sim

        except Exception as e:
            print(f"[VoiceRec] Verify error: {e}")
            return False, 0.0

    # ─────────────────────────────────────────────────────────────────
    def has_voice_print(self, user_id: int) -> bool:
        path = os.path.join(self.voice_prints_dir, f"user_{user_id}.npy")
        return os.path.exists(path)

    def delete_voice_print(self, user_id: int):
        path = os.path.join(self.voice_prints_dir, f"user_{user_id}.npy")
        if os.path.exists(path):
            os.remove(path)
