"""Speech engines: Microsoft Edge neural voices, Piper (offline) and Google Translate's voice (last resort)."""

from __future__ import annotations

import asyncio
import subprocess
import threading
import wave
from pathlib import Path
from urllib.parse import quote

from ..core import http
from ..core.deps import has
from ..media.ffmpeg import ffmpeg_exe
from .audio import wav_duration


def _pct(v: float) -> str:
    v = round(float(v or 0))
    return f"{'+' if v >= 0 else ''}{v}%"


async def edge_synth(text: str, voice: str, rate: float = 0, attempts: int = 3) -> bytes:
    """MP3 bytes. The service sometimes refuses a connection when many requests overlap; retry shortly."""
    import edge_tts

    last: Exception | None = None
    for attempt in range(attempts):
        try:
            comm = edge_tts.Communicate(text, voice, rate=_pct(rate), pitch="+0Hz")
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf += chunk["data"]
            if len(buf) < 200:
                raise RuntimeError("EDGE_EMPTY")
            return bytes(buf)
        except Exception as e:  # noqa: BLE001
            last = e
            await asyncio.sleep(0.6 * (attempt + 1))
    assert last is not None
    raise last


def edge_available() -> bool:
    return has("edge_tts")


def shift_pitch(path: Path, factor: float, rate: int) -> None:
    """Change pitch without changing duration (asetrate + atempo). Piper only."""
    if abs(factor - 1.0) < 0.02:
        return
    tmp = path.with_name(path.name + ".shift.wav")
    af = f"asetrate={round(rate * factor)},aresample={rate},atempo={1.0 / factor:.6f}"
    proc = subprocess.run(
        [ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(path), "-filter:a", af, "-ar", str(rate), str(tmp)],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("pitch shift failed: " + proc.stderr.decode("utf-8", "ignore")[-300:])
    tmp.replace(path)


class Piper:
    """Loaded on first use. Piper itself is not thread-safe, so calls are serialized."""

    def __init__(self, model: Path):
        self.model = model
        self._voice = None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.model.exists()

    def _load(self):
        if self._voice is None:
            from piper import PiperVoice

            self._voice = PiperVoice.load(str(self.model))
        return self._voice

    def synth_file(self, text: str, out: Path, pitch: float = 1.0) -> float:
        with self._lock:
            voice = self._load()
            out.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(out), "wb") as wav:
                voice.synthesize_wav(text, wav)
            rate = int(getattr(voice.config, "sample_rate", 22050))
        shift_pitch(out, pitch, rate)
        return wav_duration(out)


def split_for_google(text: str, limit: int = 170) -> list[str]:
    out: list[str] = []
    cur = ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > limit:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        out.append(cur)
    return out


async def google_tts(text: str, lang: str = "ar") -> bytes:
    bufs = []
    for part in split_for_google(text.strip()):
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl={quote(lang)}&q={quote(part)}"
        b = await http.get_bytes(url, headers={"Referer": "https://translate.google.com/"}, timeout=20)
        if len(b) < 100:
            raise RuntimeError("TTS_EMPTY")
        bufs.append(b)
        await asyncio.sleep(0.06)
    if not bufs:
        raise RuntimeError("TTS_EMPTY_TEXT")
    return b"".join(bufs)
