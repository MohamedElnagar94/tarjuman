"""Speech to text with faster-whisper, in this process (a worker thread; one model, one job at a time)."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Callable

from .core.deps import has
from .core.errors import Cancelled

log = logging.getLogger("tarjuman.asr")


def installed() -> bool:
    return has("faster_whisper")


class Whisper:
    def __init__(self, model: str, tmp: Path, threads: int = 8):
        self.model_name = model
        self.tmp = tmp
        self.threads = threads
        self._model = None
        self._lock = threading.Lock()
        self.error = ""

    @property
    def ready(self) -> bool:
        return self._model is not None

    def status(self) -> dict:
        return {"installed": installed(), "ready": self.ready, "model": self.model_name, "error": self.error[-300:]}

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            t0 = time.time()
            try:
                self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8", cpu_threads=self.threads)
            except Exception as e:  # noqa: BLE001
                self.error = f"{type(e).__name__}: {e}"
                raise
            log.info("whisper %s ready in %.1fs", self.model_name, time.time() - t0)
        return self._model

    def _transcribe(self, audio: str, on_progress: Callable[[float], None] | None, cancelled: Callable[[], bool]) -> dict:
        with self._lock:
            model = self._load()
            segments_iter, info = model.transcribe(
                audio, language=None, task="transcribe", beam_size=1, vad_filter=True, condition_on_previous_text=False
            )
            total = float(getattr(info, "duration", 0.0) or 0.0)
            segments, last = [], 0.0
            for seg in segments_iter:  # consuming the generator does the work
                if cancelled():
                    raise Cancelled()
                if on_progress and total > 0 and time.time() - last > 1.0:
                    last = time.time()
                    on_progress(min(1.0, float(seg.end) / total))
                text = (seg.text or "").strip()
                if text:
                    segments.append({"start": round(float(seg.start), 3), "end": round(float(seg.end), 3), "text": text})
            return {"segments": segments, "lang": getattr(info, "language", None) or "", "duration": total}

    async def transcribe_file(
        self, path: Path, on_progress: Callable[[float], None] | None = None, cancelled: Callable[[], bool] = lambda: False
    ) -> dict:
        return await asyncio.to_thread(self._transcribe, str(path), on_progress, cancelled)

    async def transcribe_pcm(self, pcm: bytes, sample_rate: int = 16000) -> dict:
        """Raw s16le mono audio (the extension's tab capture) -> {text, lang}."""
        self.tmp.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(suffix=".wav", dir=self.tmp)
        os.close(fd)
        try:
            with wave.open(name, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                w.writeframes(pcm)
            res = await asyncio.to_thread(self._transcribe, name, None, lambda: False)
        finally:
            Path(name).unlink(missing_ok=True)
        return {"text": " ".join(s["text"] for s in res["segments"]).strip(), "lang": res["lang"]}
