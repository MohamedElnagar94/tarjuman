"""Speak text: Edge → Piper (Arabic, offline) → Google. Every (voice, rate, text) is cached on disk
with its measured duration, and the real speaking speed of each voice is learned as it is used."""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from ..core.errors import AppError
from ..core.store import Debounced, read_json, write_json
from ..core.text import chars_of
from .audio import decode_to_pcm, duration_of, trim_silence, write_wav
from .catalog import CHARS_PER_SEC, Voice, resolve_voice, voices_for
from .engines import Piper, edge_available, edge_synth, google_tts
from .gate import PLAY, PriorityGate
from .pronounce import PronunciationDict


@dataclass
class TtsResult:
    buf: bytes
    mime: str
    duration: float
    engine: str
    fallback: bool = False


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def clip_key(v: Voice, rate: int, text: str) -> str:
    # Same key layout as the prototype, so an existing voice cache can be reused.
    return sha1(f"{v.lang}|{v.engine}|{v.voice}|{v.pitch:g}|{rate}|{text}")


def clamp_rate(rate) -> int:
    try:
        r = round(float(rate or 0))
    except (TypeError, ValueError):
        r = 0
    return max(-30, min(80, r))


class TtsService:
    def __init__(self, cache_dir: Path, piper_model: Path, pronounce: PronunciationDict):
        self.dir = cache_dir
        self.piper = Piper(piper_model)
        self.pronounce = pronounce
        # Measured: 8 parallel requests give the most throughput; more only queue up on Microsoft's side.
        self.gate = PriorityGate(8)
        self.meta: dict[str, float] = {}  # clip key -> duration
        self.cps: dict[str, dict] = {}  # voice key -> {"cps": float, "n": int}
        self.stats = {"edge": 0, "piper": 0, "fallback": 0, "google": 0}
        self._inflight: dict[str, asyncio.Future] = {}
        self._meta_file = cache_dir / "_meta.json"
        self._save_meta = Debounced(self._write_meta, 3.0)
        self.ready = False
        self._written = 0
        self.cache_limit = 0  # bytes; 0 = no limit (set by the app from config)

    def prune(self) -> int:
        """Keep the clip cache under its limit (least recently used first)."""
        if not self.cache_limit:
            return 0
        from ..storage import prune_clips

        n = prune_clips(self.dir, self.cache_limit, self.meta)
        if n:
            self._save_meta.touch()
        return n

    # ---------------- status / catalog ----------------

    def load(self) -> None:
        j = read_json(self._meta_file, {})
        self.meta = {k: float(d) for k, d in (j.get("durations") or {}).items() if d}
        self.cps = dict(j.get("cps") or {})

    def _write_meta(self) -> None:
        write_json(self._meta_file, {"durations": self.meta, "cps": self.cps})

    def flush(self) -> None:
        self._save_meta.flush()

    def status(self) -> dict:
        return {
            "installed": True,
            "ready": self.ready,
            "edge": edge_available(),
            "piper": self.piper.available,
            "stats": self.stats,
        }

    def voices(self, lang: str) -> list[dict]:
        return voices_for(lang, self.piper.available)

    # ---------------- speaking speed ----------------

    def voice_cps(self, v: Voice) -> float:
        learned = self.cps.get(v.key)
        if learned:
            return float(learned["cps"])
        t = CHARS_PER_SEC.get(v.engine, CHARS_PER_SEC["edge"])
        return t.get(v.lang, t["default"])

    def learn_cps(self, v: Voice, text: str, rate: float, duration: float) -> None:
        n = chars_of(text)
        if v.engine != "edge" or not duration or duration <= 1 or n < 15:
            return
        obs = n / (duration * (1 + rate / 100))
        if obs < 5 or obs > 30:
            return
        prev = self.cps.get(v.key)
        self.cps[v.key] = {"cps": prev["cps"] * 0.9 + obs * 0.1 if prev else obs, "n": (prev["n"] if prev else 0) + 1}
        self._save_meta.touch()

    def natural_duration(self, text: str, v: Voice) -> float:
        return chars_of(text) / self.voice_cps(v)

    def _set_meta(self, key: str, duration: float) -> None:
        if duration and duration > 0:
            self.meta[key] = duration
            self._save_meta.touch()

    # ---------------- live: bytes for the browser ----------------

    async def speak(self, text: str, lang: str = "ar", voice: str = "", rate=0, *, priority: int = PLAY) -> TtsResult:
        text = self.pronounce.apply(text).strip()
        if not text:
            raise AppError("NO_TEXT")
        v = resolve_voice(voice, lang)
        r = clamp_rate(rate)
        key = clip_key(v, r, text)
        if key in self._inflight:
            # The same sentence is already being made: wait for it, and hurry it if this caller is more urgent.
            self.gate.bump(key, priority)
            return await asyncio.shield(self._inflight[key])
        fut = asyncio.ensure_future(self._speak_uncached(text, v, r, key, priority))
        self._inflight[key] = fut
        try:
            return await asyncio.shield(fut)
        finally:
            if fut.done():
                self._inflight.pop(key, None)
            else:
                fut.add_done_callback(lambda _f: self._inflight.pop(key, None))

    async def _speak_uncached(self, text: str, v: Voice, rate: int, key: str, priority: int) -> TtsResult:
        for ext, mime in (("mp3", "audio/mpeg"), ("wav", "audio/wav")):
            f = self.dir / f"{key}.{ext}"
            if f.exists():
                buf = f.read_bytes()
                try:
                    os.utime(f)  # marks it recently used, for the cache's size limit
                except OSError:
                    pass
                duration = self.meta.get(key) or duration_of(buf, mime)
                self._set_meta(key, duration)
                return TtsResult(buf, mime, duration, v.engine)

        attempts = [v]
        if v.engine == "edge" and v.lang == "ar" and self.piper.available:
            attempts.append(Voice("piper", "piper", "ar", 1.0))
        for a in attempts:
            try:
                res = await self.gate.run(priority, lambda a=a: self._synth_bytes(text, a, rate if a.engine == "edge" else 0), key if a is v else None)
            except Exception:  # noqa: BLE001 — try the next engine
                continue
            if a is v:
                # A fallback voice is never cached under the requested voice's key; otherwise this
                # sentence would keep the wrong voice and the wrong duration forever.
                self.learn_cps(a, text, rate, res.duration)
                try:
                    (self.dir / f"{key}.{'mp3' if res.mime == 'audio/mpeg' else 'wav'}").write_bytes(res.buf)
                    self._set_meta(key, res.duration)
                except OSError:
                    pass
                self._written += 1
                if self._written % 200 == 0:
                    asyncio.ensure_future(asyncio.to_thread(self.prune))
                self.stats[a.engine] = self.stats.get(a.engine, 0) + 1
                return res
            self.stats["fallback"] += 1
            return replace(res, fallback=True)

        self.stats["google"] += 1
        gkey = sha1(f"{v.lang}|{text}")
        gfile = self.dir / f"{gkey}.mp3"
        if gfile.exists():
            buf = gfile.read_bytes()
        else:
            buf = await google_tts(text, v.lang)
            try:
                gfile.write_bytes(buf)
            except OSError:
                pass
        return TtsResult(buf, "audio/mpeg", 0.0, "google", fallback=True)

    async def _synth_bytes(self, text: str, v: Voice, rate: int) -> TtsResult:
        if v.engine == "edge":
            data = await edge_synth(text, v.voice, rate)
            sr, pcm = await asyncio.to_thread(decode_to_pcm, data)
            return TtsResult(data, "audio/mpeg", round(len(pcm) / float(sr), 3), "edge")
        if not self.piper.available:
            raise RuntimeError("PIPER_NOT_AVAILABLE")
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            duration = await asyncio.to_thread(self.piper.synth_file, text, Path(tmp), v.pitch)
            return TtsResult(Path(tmp).read_bytes(), "audio/wav", duration, "piper")
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    # ---------------- dubbed MP4: WAV files for the mixer ----------------

    async def synth_wav(self, text: str, v: Voice, rate: int, out: Path) -> tuple[float, bool]:
        """Write the sentence as mono 16-bit WAV (silence trimmed). Returns (duration, used_fallback)."""
        text = self.pronounce.apply(text)
        if v.engine == "edge":
            try:
                data = await self.gate.run(PLAY, lambda: edge_synth(text, v.voice, rate))
                return await asyncio.to_thread(self._mp3_to_wav, data, out, True), False
            except Exception:  # noqa: BLE001
                if not (v.lang == "ar" and self.piper.available):
                    data = await google_tts(text, v.lang)
                    return await asyncio.to_thread(self._mp3_to_wav, data, out, False), True
                return await asyncio.to_thread(self.piper.synth_file, text, out, 1.0), True
        if self.piper.available:
            return await asyncio.to_thread(self.piper.synth_file, text, out, v.pitch), False
        data = await google_tts(text, v.lang)
        return await asyncio.to_thread(self._mp3_to_wav, data, out, False), True

    @staticmethod
    def _mp3_to_wav(data: bytes, out: Path, trim: bool) -> float:
        sr, pcm = decode_to_pcm(data)
        if trim:
            pcm = trim_silence(sr, pcm)
        write_wav(out, sr, pcm)
        return round(len(pcm) / float(sr), 3)

    async def warm_up(self) -> None:
        """The first connection to the voice service takes seconds; make it before the user needs it."""
        try:
            await self.speak("أهلًا", "ar", "", 0, priority=0)
        except Exception:  # noqa: BLE001
            pass
        self.ready = True
