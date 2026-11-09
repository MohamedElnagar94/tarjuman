"""Speaker pitch (F0) from a video's audio: used to pick a male or female voice per sentence.

    python -m tarjuman.media.pitch <video> <ranges.json [[start,end],...]>  ->  {"f0": [118.2, 0, 205.1]}
"""

from __future__ import annotations

import json
import sys

import numpy as np


def pcm_from_video(path: str, rate: int = 16000, max_sec: float = 90.0) -> np.ndarray:
    """Decode a video's audio to mono 16 kHz (the first ``max_sec`` seconds)."""
    import av

    res = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=rate)
    chunks, total, limit = [], 0, int(max_sec * rate)
    with av.open(path) as container:
        for frame in container.decode(audio=0):
            for f in res.resample(frame):
                arr = np.frombuffer(bytes(f.planes[0]), dtype=np.int16)[: f.samples]
                chunks.append(arr)
                total += len(arr)
            if total >= limit:
                break
    if not chunks:
        return np.zeros(0, dtype=np.int16)
    return np.concatenate(chunks)[:limit]


def estimate_f0(pcm: np.ndarray, rate: int = 16000, fmin: float = 70.0, fmax: float = 350.0) -> float:
    """Median fundamental frequency by autocorrelation, with octave-error correction."""
    if pcm is None or len(pcm) < rate * 0.5:
        return 0.0
    frame, hop = int(0.04 * rate), int(0.02 * rate)
    min_lag, max_lag = max(2, int(rate / fmax)), int(rate / fmin)
    n_frames = max(1, (len(pcm) - frame) // hop)
    stride = max(1, n_frames // 400)
    f0s = []
    for idx in range(0, n_frames, stride):
        f = pcm[idx * hop : idx * hop + frame].astype(np.float64)
        if len(f) < frame:
            break
        f = f - f.mean()
        if float(np.sqrt(np.mean(f * f))) / 32768.0 < 0.004:
            continue
        corr = np.correlate(f, f, mode="full")[frame - 1 :]
        if len(corr) == 0 or corr[0] <= 0:
            continue
        corr = corr / corr[0]
        if max_lag >= len(corr):
            continue
        lag = int(np.argmax(corr[min_lag:max_lag])) + min_lag
        peak = corr[lag]
        if peak <= 0.3:
            continue
        # Octave correction: a strong peak at a multiple of the lag means a lower pitch.
        best_lag, best_peak = lag, peak
        for mult in (2, 3):
            l2 = lag * mult
            if l2 + 4 >= len(corr):
                break
            lo, hi = max(1, int(l2 * 0.92)), min(len(corr) - 1, int(l2 * 1.08))
            if hi <= lo:
                continue
            l2b = lo + int(np.argmax(corr[lo:hi]))
            if corr[l2b] > max(0.22, best_peak * 0.72):
                best_lag, best_peak = l2b, corr[l2b]
        f0s.append(rate / best_lag)
    return float(np.median(f0s)) if f0s else 0.0


def sentence_f0(video: str, ranges: list[list[float]]) -> list[float]:
    last_end = max((float(e) for _, e in ranges), default=0.0)
    pcm = pcm_from_video(video, 16000, last_end + 1.0)
    out = []
    for s, e in ranges:
        seg = pcm[int(float(s) * 16000) : int(float(e) * 16000)]
        out.append(round(estimate_f0(seg, 16000), 1) if len(seg) >= 8000 else 0.0)
    return out


if __name__ == "__main__":
    with open(sys.argv[2], "r", encoding="utf-8") as fh:
        print(json.dumps({"f0": sentence_f0(sys.argv[1], json.load(fh))}), flush=True)
