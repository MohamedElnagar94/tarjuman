"""What a media file holds (audio only, or a picture that moves) and its waveform for the audio player."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

log = logging.getLogger("tarjuman.media")

COVER_CODECS = {"mjpeg", "png", "bmp", "gif", "webp", "tiff"}
PEAK_RATE = 4000  # Hz: plenty for a picture of the loudness
PEAK_BUCKETS = 1600


def probe(path: Path) -> dict[str, Any]:
    """{"kind": "audio"|"video", "duration": seconds}. Empty when the file can't be read."""
    try:
        import av  # type: ignore

        with av.open(str(path)) as c:
            video = False
            for s in c.streams:
                if s.type != "video":
                    continue
                name = (getattr(s.codec_context, "name", "") or "").lower()
                frames = int(getattr(s, "frames", 0) or 0)
                if name in COVER_CODECS and frames <= 1:
                    continue  # the cover art of a song or podcast
                video = True
            duration = float(c.duration / 1_000_000) if c.duration else 0.0
            if not duration:
                a = next((s for s in c.streams if s.type == "audio"), None)
                if a is not None and a.duration and a.time_base:
                    duration = float(a.duration * a.time_base)
            return {"kind": "video" if video else "audio", "duration": round(duration, 3)}
    except Exception as e:  # noqa: BLE001
        log.info("cannot probe %s: %r", path.name, e)
        return {}


def repair_stream_file(path: Path) -> bool:
    """A recording made in a browser (MediaRecorder) is written as a stream: no length and no index,
    so a player can't show its duration or seek in it. Copying it once (no re-encoding) fixes both."""
    if path.suffix.lower() not in (".webm", ".weba", ".ogg", ".oga", ".mka", ".opus"):
        return False
    import subprocess

    from .ffmpeg import ffmpeg_exe

    tmp = path.with_name(path.stem + ".fixed" + path.suffix)
    try:
        subprocess.run(
            [ffmpeg_exe(), "-nostdin", "-y", "-loglevel", "error", "-i", str(path), "-c", "copy", str(tmp)],
            capture_output=True, check=True, timeout=600, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if tmp.stat().st_size < 1000:
            raise ValueError("empty result")
        tmp.replace(path)
        return True
    except Exception as e:  # noqa: BLE001
        log.info("could not repair %s: %r", path.name, e)
        tmp.unlink(missing_ok=True)
        return False


def peaks(path: Path, buckets: int = PEAK_BUCKETS) -> dict[str, Any]:
    """The loudest point of each slice of the file (0..1, the loudest slice = 1), as the audio player
    draws it. Decoded once and kept next to the file."""
    import av  # type: ignore
    import numpy as np

    block = PEAK_RATE // 100  # 10 ms
    maxima: list[np.ndarray] = []
    rest = np.zeros(0, np.float32)
    with av.open(str(path)) as c:
        stream = next((s for s in c.streams if s.type == "audio"), None)
        if stream is None:
            return {"peaks": [], "duration": 0.0}
        resampler = av.AudioResampler(format="flt", layout="mono", rate=PEAK_RATE)
        for frame in c.decode(stream):
            for out in resampler.resample(frame):
                x = np.abs(out.to_ndarray().reshape(-1)).astype(np.float32)
                x = np.concatenate([rest, x])
                n = len(x) // block * block
                if n:
                    maxima.append(x[:n].reshape(-1, block).max(axis=1))
                rest = x[n:]
    if len(rest):
        maxima.append(np.array([rest.max()], np.float32))
    if not maxima:
        return {"peaks": [], "duration": 0.0}
    m = np.concatenate(maxima)
    duration = len(m) * block / PEAK_RATE
    n = max(1, min(buckets, len(m)))
    edges = np.linspace(0, len(m), n + 1).astype(int)
    out = np.array([m[a:b].max() if b > a else 0.0 for a, b in zip(edges[:-1], edges[1:])], np.float32)
    top = float(np.percentile(out, 99.5)) or float(out.max()) or 1.0
    out = np.clip(out / top, 0, 1)
    return {"peaks": [round(float(v), 3) for v in out], "duration": round(duration, 3)}


def small_peaks(full: list[float], n: int = 48) -> list[float]:
    """A thumbnail of the waveform for the library list."""
    if not full:
        return []
    step = len(full) / n
    return [round(max(full[math.floor(i * step): max(math.floor(i * step) + 1, math.floor((i + 1) * step))]), 2) for i in range(n)]
