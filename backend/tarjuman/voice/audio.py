"""PCM helpers: decode, trim, write WAV, measure."""

from __future__ import annotations

import io
import os
import wave

import numpy as np


def decode_to_pcm(data: bytes) -> tuple[int, np.ndarray]:
    """mp3/wav bytes -> (sample rate, int16 mono)."""
    import av

    with av.open(io.BytesIO(data)) as c:
        stream = c.streams.audio[0]
        rate = stream.codec_context.sample_rate or 24000
        res = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=rate)
        chunks = []
        for frame in c.decode(audio=0):
            for f in res.resample(frame):
                chunks.append(np.frombuffer(bytes(f.planes[0]), dtype=np.int16)[: f.samples])
        for f in res.resample(None):
            chunks.append(np.frombuffer(bytes(f.planes[0]), dtype=np.int16)[: f.samples])
    return rate, (np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16))


def write_wav(path: str | os.PathLike, rate: int, pcm: np.ndarray) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.astype(np.int16).tobytes())


def wav_duration(path: str | os.PathLike) -> float:
    with wave.open(str(path), "rb") as w:
        return round(w.getnframes() / float(w.getframerate() or 22050), 3)


def trim_silence(rate: int, pcm: np.ndarray, thresh: int = 300, keep: float = 0.04) -> np.ndarray:
    """Remove the silence Edge leaves around speech (~0.1 s) so the timing is exact."""
    if len(pcm) == 0:
        return pcm
    loud = np.nonzero(np.abs(pcm.astype(np.int32)) > thresh)[0]
    if len(loud) == 0:
        return pcm
    pad = int(keep * rate)
    return pcm[max(0, loud[0] - pad) : min(len(pcm), loud[-1] + pad)]


def duration_of(buf: bytes, mime: str) -> float:
    """Duration without decoding: WAV from its header; Edge MP3 is a constant 48 kbps."""
    if mime == "audio/wav" and len(buf) > 44 and buf[:4] == b"RIFF":
        byte_rate = int.from_bytes(buf[28:32], "little")
        return round((len(buf) - 44) / byte_rate, 3) if byte_rate else 0.0
    if mime == "audio/mpeg":
        return round(len(buf) * 8 / 48000, 3)
    return 0.0
