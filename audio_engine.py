"""
audio_engine.py — Microphone capture and Google Speech transcription.

Design
------
- Recording runs on sounddevice's internal callback thread. Frames go into
  a thread-safe queue.
- stop_recording() just closes the stream — it is safe to call from any thread.
- transcribe() is always synchronous and should be called on a background
  worker thread (never the Qt main thread).
- Audio is stored as int16 PCM so SpeechRecognition can read the WAV natively.
"""

import io
import queue
import threading

import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd
import speech_recognition as sr


class AudioEngine:
    """Thread-safe audio capture + transcription engine."""

    SAMPLE_RATE = 16_000  # Hz — Google Speech works best at 16 kHz

    def __init__(self) -> None:
        self._q: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def start_recording(self) -> None:
        """Start capturing audio. Safe to call from any thread."""
        with self._lock:
            if self._recording:
                return
            self._q = queue.Queue()  # clear any stale data
            self._recording = True

        print("[AudioEngine] Microphone active. Listening…")
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop_recording(self) -> None:
        """Stop capturing. Returns immediately — does NOT transcribe."""
        with self._lock:
            if not self._recording:
                return
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[AudioEngine] Microphone closed.")

    def transcribe(self) -> str:
        """
        Drain the buffer and return a transcription string.
        Must be called AFTER stop_recording(). Blocks for the duration of the
        Google Speech API call — run this on a background thread.
        """
        data = []
        while not self._q.empty():
            data.append(self._q.get_nowait())

        if not data:
            print("[AudioEngine] No audio data captured.")
            return ""

        # Concatenate float32 frames and convert to int16 PCM.
        # SpeechRecognition only reads 8-bit / 16-bit PCM WAV natively.
        float_audio = np.concatenate(data, axis=0)
        pcm_audio = (float_audio * 32767).clip(-32768, 32767).astype(np.int16)

        wav_io = io.BytesIO()
        wav.write(wav_io, self.SAMPLE_RATE, pcm_audio)
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(wav_io) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            print(f"[AudioEngine] Transcribed: '{text}'")
            return text
        except sr.UnknownValueError:
            print("[AudioEngine] Could not understand audio.")
            return ""
        except sr.RequestError as exc:
            print(f"[AudioEngine] Google Speech API error: {exc}")
            return ""
        except Exception as exc:  # noqa: BLE001
            print(f"[AudioEngine] Unexpected transcription error: {exc}")
            return ""

    # ── Internal ─────────────────────────────────────────────────────────

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """sounddevice callback — runs on the audio I/O thread."""
        with self._lock:
            if self._recording:
                self._q.put(indata.copy())
