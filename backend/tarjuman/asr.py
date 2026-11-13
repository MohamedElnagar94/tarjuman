"""Speech to text with faster-whisper, in this process (a worker thread; one model, one job at a time).

The settings (model, device, language, how Arabic is written, audio cleanup) come from
``asr_settings``; they apply to the next transcription, and the model is swapped when they change.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable

from .asr_settings import MODELS, AsrSettings, hub_bytes, model_downloaded
from .core.deps import has
from .core.errors import Cancelled

log = logging.getLogger("tarjuman.asr")

SAMPLE_RATE = 16000
# ffmpeg filters for "clean the audio first": rumble and hiss out, gentle denoise, even loudness.
ENHANCE_FILTER = "highpass=f=70,lowpass=f=7800,afftdn=nf=-28:tn=1,dynaudnorm=f=200:g=11"


def installed() -> bool:
    return has("faster_whisper")


class Whisper:
    def __init__(self, settings: AsrSettings, tmp: Path):
        self.settings = settings
        self.tmp = tmp
        self._model = None
        self._key: tuple[str, str, str] | None = None  # (model, device, compute) of the loaded model
        self._lock = threading.Lock()
        self.error = ""
        self.fallback = ""  # why the GPU wasn't used though it was asked for
        self.cuda_broken = False
        self.loading: dict[str, Any] | None = None  # {model, started, base} while loading/downloading

    # ------------------------------------------------------------------ state

    @property
    def model_name(self) -> str:
        return self._key[0] if self._key else self.effective()["model"]

    @property
    def ready(self) -> bool:
        return self._model is not None

    def effective(self, duration: float | None = None) -> dict[str, Any]:
        eff = self.settings.effective(duration=duration)
        if self.cuda_broken and eff["device"] == "cuda":
            eff.update(device="cpu", compute="int8")
        return eff

    def _is_loaded(self, eff: dict[str, Any]) -> bool:
        return self._model is not None and self._key == (eff["model"], eff["device"], eff["compute"])

    def status(self) -> dict:
        eff = self.effective()
        loading = None
        if self.loading:
            size = MODELS.get(self.loading["model"], {}).get("size", 0) * 1_000_000
            # Only a download has a percentage; loading a model already on disk is "preparing".
            dl = self.loading.get("download") and size
            got = max(0, hub_bytes() - self.loading["base"]) if dl else 0
            loading = {
                "model": self.loading["model"],
                "progress": min(99, round(got / size * 100)) if dl else None,
                "seconds": round(time.time() - self.loading["started"]),
            }
        return {
            "installed": installed(),
            # A model is in memory (auto may still pick another one for a recording of another length).
            "ready": self._model is not None and not self.loading,
            "model": self._key[0] if self._key else eff["model"],
            "device": self._key[1] if self._key else eff["device"],
            "loading": loading,
            "error": self.error[-300:],
            "fallback": self.fallback,
        }

    # ------------------------------------------------------------------ model

    def _load(self, eff: dict[str, Any]):
        if self._is_loaded(eff):
            return self._model
        from faster_whisper import WhisperModel

        self._model = None
        self._key = None
        on_disk = model_downloaded(eff["model"])
        self.loading = {"model": eff["model"], "started": time.time(), "base": 0 if on_disk else hub_bytes(), "download": not on_disk}
        t0 = time.time()
        try:
            try:
                model = WhisperModel(eff["model"], device=eff["device"], compute_type=eff["compute"], cpu_threads=eff["threads"])
            except Exception as e:  # noqa: BLE001
                if eff["device"] != "cuda":
                    raise
                self._gpu_failed(e)
                eff.update(device="cpu", compute="int8")
                model = WhisperModel(eff["model"], device="cpu", compute_type="int8", cpu_threads=eff["threads"])
        except Exception as e:  # noqa: BLE001
            self.error = f"{type(e).__name__}: {e}"
            raise
        finally:
            self.loading = None
        self._model, self._key, self.error = model, (eff["model"], eff["device"], eff["compute"]), ""
        log.info("whisper %s on %s ready in %.1fs", eff["model"], eff["device"], time.time() - t0)
        return model

    def _gpu_failed(self, e: BaseException) -> None:
        self.cuda_broken = True
        self.fallback = f"تعذّر تشغيل النموذج على بطاقة الرسوميات ({type(e).__name__}: {str(e)[:160]})، فاستُعمل المعالج."
        log.warning("whisper on the GPU failed, using the CPU: %r", e)

    def forget_model(self, name: str) -> bool:
        """Lets go of a model in memory before its files are deleted. False while it is working."""
        if not self._lock.acquire(blocking=False):
            return False
        try:
            if self._key and self._key[0] == name:
                self._model, self._key = None, None
            return True
        finally:
            self._lock.release()

    def prepare(self) -> bool:
        """Downloads and loads the chosen model in the background (Settings -> "prepare now")."""
        if not installed() or self.loading or self.status()["ready"]:
            return False

        def work() -> None:
            try:
                with self._lock:
                    self._load(self.effective())
            except Exception as e:  # noqa: BLE001
                log.warning("whisper prepare failed: %r", e)

        threading.Thread(target=work, name="whisper-prepare", daemon=True).start()
        return True

    # ------------------------------------------------------------------ audio

    def _decode(self, path: str, enhance: bool) -> Any:
        """16 kHz mono float audio. With "enhance", ffmpeg cleans it on the way."""
        from faster_whisper.audio import decode_audio

        if not enhance:
            return decode_audio(path, sampling_rate=SAMPLE_RATE)
        import numpy as np

        from .media.ffmpeg import ffmpeg_exe

        try:
            out = subprocess.run(
                [ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-i", path, "-vn", "-af", ENHANCE_FILTER,
                 "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"],
                capture_output=True, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout
            if not out:
                raise ValueError("no audio")
            return np.frombuffer(out, np.int16).astype(np.float32) / 32768.0
        except Exception as e:  # noqa: BLE001 — cleaning is a bonus; the plain audio still works
            log.warning("audio cleanup failed (%r); using the original audio", e)
            return decode_audio(path, sampling_rate=SAMPLE_RATE)

    # ------------------------------------------------------------------ transcription

    def _transcribe(
        self,
        audio: str,
        on_progress: Callable[[float], None] | None,
        cancelled: Callable[[], bool],
        on_phase: Callable[[str], None] | None = None,
    ) -> dict:
        phase = on_phase or (lambda _s: None)
        from .media.probe import probe

        length = probe(Path(audio)).get("duration") or None
        with self._lock:
            eff = self.effective(length)
            if not self._is_loaded(eff):
                phase(f"تحضير نموذج Whisper ({eff['model']})")
            try:
                return self._run(self._load(eff), eff, audio, on_progress, cancelled, phase)
            except Cancelled:
                raise
            except Exception as e:  # noqa: BLE001 — a GPU can fail only at the first real work
                if eff["device"] != "cuda" or not _looks_like_gpu_error(e):
                    raise
                self._gpu_failed(e)
                eff = self.effective(length)
                phase(f"تحضير نموذج Whisper ({eff['model']}) على المعالج")
                return self._run(self._load(eff), eff, audio, on_progress, cancelled, phase)

    def _run(self, model, eff: dict[str, Any], audio: str, on_progress, cancelled, phase) -> dict:
        phase("قراءة الصوت وتنقيته" if eff["enhance"] else "قراءة الصوت")
        samples = self._decode(audio, eff["enhance"])
        lang = eff["language"]
        prob = 1.0
        if lang is None and eff["prompt"]:
            # Detect first, so the Arabic writing hint is given only to Arabic speech.
            phase("تحديد لغة الكلام")
            try:
                lang, prob, _all = model.detect_language(samples, vad_filter=eff["vad"], language_detection_segments=3)
            except Exception as e:  # noqa: BLE001
                log.info("language detection failed (%r); Whisper will detect it", e)
                lang = None
        prompt = eff["prompt"] if lang == "ar" and eff["prompt"] else None
        if cancelled():
            raise Cancelled()
        phase(f"تفريغ الكلام بنموذج {eff['model']}")
        segments_iter, info = model.transcribe(
            samples,
            language=lang,
            task="transcribe",
            beam_size=eff["beam"],
            best_of=eff["beam"],
            vad_filter=eff["vad"],
            vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300} if eff["vad"] else None,
            condition_on_previous_text=False,
            initial_prompt=prompt,
            hotwords=eff.get("hotwords") or None,
            language_detection_segments=3,
            # Word times let a long stretch of speech be cut into sentences that each show on time.
            word_timestamps=True,
        )
        total = float(getattr(info, "duration", 0.0) or len(samples) / SAMPLE_RATE)
        segments, last = [], 0.0
        for seg in segments_iter:  # consuming the generator does the work
            if cancelled():
                raise Cancelled()
            if on_progress and total > 0 and time.time() - last > 1.0:
                last = time.time()
                on_progress(min(1.0, float(seg.end) / total))
            text = (seg.text or "").strip()
            if text and not _is_prompt_echo(text, prompt):
                segments.extend(split_sentences(seg))
        return {
            "segments": segments,
            "lang": getattr(info, "language", None) or lang or "",
            "langProb": round(float(getattr(info, "language_probability", None) or prob), 3),
            "duration": total,
            "model": eff["model"],
            "device": eff["device"],
        }

    async def transcribe_file(
        self,
        path: Path,
        on_progress: Callable[[float], None] | None = None,
        cancelled: Callable[[], bool] = lambda: False,
        on_phase: Callable[[str], None] | None = None,
    ) -> dict:
        return await asyncio.to_thread(self._transcribe, str(path), on_progress, cancelled, on_phase)

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


SENTENCE_END = (".", "?", "!", "؟", "…", "۔")
SOFT_END = ("،", ",", "؛", ";", ":")
MAX_WORDS = 10


def split_sentences(seg: Any) -> list[dict]:
    """Whisper hands back up to 30 s of speech as one segment. Shown as one subtitle it lags behind
    the voice, and "repeat this sentence" repeats a paragraph. With the time of every word it is cut
    where a sentence ends (or at a comma once it gets long)."""
    whole = {"start": round(float(seg.start), 3), "end": round(float(seg.end), 3), "text": (seg.text or "").strip()}
    words = [w for w in (getattr(seg, "words", None) or []) if (w.word or "").strip()]
    if len(words) < 2:
        return [whole]
    out: list[dict] = []
    cur: list[Any] = []

    def flush() -> None:
        if cur:
            text = "".join(w.word for w in cur).strip()
            if text:
                out.append({"start": round(float(cur[0].start), 3), "end": round(float(cur[-1].end), 3), "text": text})
            cur.clear()

    for i, w in enumerate(words):
        cur.append(w)
        token = w.word.strip()
        last = i == len(words) - 1
        if last:
            break
        if token.endswith(SENTENCE_END) and len(cur) >= 2:
            flush()
        elif len(cur) >= MAX_WORDS and token.endswith(SOFT_END):
            flush()
        elif len(cur) >= MAX_WORDS * 2:
            flush()
    flush()
    if len(out) > 1 and len(out[-1]["text"].split()) < 2:
        tail = out.pop()  # a lone last word joins the sentence before it
        out[-1] = {"start": out[-1]["start"], "end": tail["end"], "text": out[-1]["text"] + " " + tail["text"]}
    return out or [whole]


def _looks_like_gpu_error(e: BaseException) -> bool:
    s = str(e).lower()
    return any(w in s for w in ("cuda", "cublas", "cudnn", "gpu", "device"))


def _is_prompt_echo(text: str, prompt: str | None) -> bool:
    """On silence Whisper sometimes "says" the hint it was given; such a line is dropped."""
    if not prompt:
        return False

    def norm(s: str) -> str:
        return "".join(ch for ch in s if ch.isalnum())

    a, b = norm(text), norm(prompt)
    return len(a) > 8 and (a in b or b in a)
