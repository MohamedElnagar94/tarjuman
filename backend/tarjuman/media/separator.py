"""Separate speech from the background (music, effects) so the dub can replace the original voice.

MDX-Net from Ultimate Vocal Remover (UVR-MDX-NET-Inst_HQ_3, outputs the instrumental) on onnxruntime,
CPU only, no PyTorch.

    python -m tarjuman.media.separator --model UVR-MDX-NET-Inst_HQ_3.onnx --input video.mp4 --out background.wav

stdout: JSON progress lines {"progress": 0.42}, then {"ok": true, "out": "...", "seconds": 123.4}.
"""

from __future__ import annotations

import argparse
import json
import os
import wave

import numpy as np

SR = 44100
# Model settings (from UVR's model data for Inst_HQ_3)
N_FFT = 6144
HOP = 1024
DIM_F = 3072
DIM_T = 256
COMPENSATE = 1.022
CHUNK = HOP * (DIM_T - 1)  # samples that produce exactly 256 frames
TRIM = N_FFT // 2
GEN = CHUNK - 2 * TRIM  # the clean middle of each chunk (edges dropped)
N_BINS = N_FFT // 2 + 1
WINDOW = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)).astype(np.float32)  # periodic Hann


def emit(obj: dict) -> None:
    print(json.dumps(obj), flush=True)


def stft(x: np.ndarray) -> np.ndarray:
    """[..., CHUNK] -> complex [..., N_BINS, DIM_T] (like torch.stft with center=True, reflect padding)."""
    pad = N_FFT // 2
    xp = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad, pad)], mode="reflect")
    n_frames = 1 + (xp.shape[-1] - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n_frames)[:, None]
    spec = np.fft.rfft(xp[..., idx] * WINDOW, axis=-1)
    return np.swapaxes(spec, -1, -2)


def istft(spec: np.ndarray, length: int) -> np.ndarray:
    """Inverse of stft: overlap-add with the same window, divided by the summed squared window."""
    frames = np.fft.irfft(np.swapaxes(spec, -1, -2), n=N_FFT, axis=-1) * WINDOW
    n_frames = frames.shape[-2]
    total = N_FFT + HOP * (n_frames - 1)
    out = np.zeros(frames.shape[:-2] + (total,), dtype=np.float32)
    norm = np.zeros(total, dtype=np.float32)
    w2 = WINDOW**2
    for t in range(n_frames):
        s = t * HOP
        out[..., s : s + N_FFT] += frames[..., t, :]
        norm[s : s + N_FFT] += w2
    out /= np.maximum(norm, 1e-8)
    pad = N_FFT // 2
    return out[..., pad : pad + length]


def separate(session, mix: np.ndarray, batch: int = 2) -> np.ndarray:
    n = mix.shape[1]
    pad_end = GEN - n % GEN
    mixp = np.concatenate([np.zeros((2, TRIM), np.float32), mix, np.zeros((2, pad_end + TRIM), np.float32)], axis=1)
    starts = list(range(0, n + pad_end, GEN))
    out = np.zeros((2, n + pad_end), np.float32)
    in_name = session.get_inputs()[0].name
    for b0 in range(0, len(starts), batch):
        group = starts[b0 : b0 + batch]
        spec = stft(np.stack([mixp[:, s : s + CHUNK] for s in group]))  # [B, 2, N_BINS, DIM_T]
        x = np.stack([spec.real, spec.imag], axis=2).reshape(len(group), 4, N_BINS, DIM_T)[:, :, :DIM_F]
        y = session.run(None, {in_name: x.astype(np.float32)})[0]  # [B, 4, DIM_F, DIM_T]
        y = np.concatenate([y, np.zeros((len(group), 4, N_BINS - DIM_F, DIM_T), np.float32)], axis=2)
        y = y.reshape(len(group), 2, 2, N_BINS, DIM_T)
        wav = istft(y[:, :, 0] + 1j * y[:, :, 1], CHUNK)
        for k, s in enumerate(group):
            out[:, s : s + GEN] = wav[k, :, TRIM : CHUNK - TRIM]
        emit({"progress": round(min(1.0, (b0 + len(group)) / len(starts)), 3)})
    return out[:, :n] * COMPENSATE


def write_wav(path: str, audio: np.ndarray) -> None:
    pcm = (np.clip(audio.T, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _run_chunks(session, in_name: str, chunks: list[np.ndarray]) -> list[np.ndarray]:
    """The model on a few CHUNK-long pieces; returns the clean middle (GEN samples) of each."""
    spec = stft(np.stack(chunks))
    x = np.stack([spec.real, spec.imag], axis=2).reshape(len(chunks), 4, N_BINS, DIM_T)[:, :, :DIM_F]
    y = session.run(None, {in_name: x.astype(np.float32)})[0]
    y = np.concatenate([y, np.zeros((len(chunks), 4, N_BINS - DIM_F, DIM_T), np.float32)], axis=2)
    y = y.reshape(len(chunks), 2, 2, N_BINS, DIM_T)
    wav = istft(y[:, :, 0] + 1j * y[:, :, 1], CHUNK)
    return [wav[k, :, TRIM : CHUNK - TRIM] * COMPENSATE for k in range(len(chunks))]


def separate_stream(session, frames, write, total: int = 0, batch: int = 2) -> int:
    """Same result as ``separate``, without holding the whole track in memory: audio comes in as
    [2, k] float32 pieces from ``frames``, and ``write(background, mix)`` receives the output in order,
    a few seconds at a time. Memory stays a few MB however long the video is. Returns the sample count."""
    in_name = session.get_inputs()[0].name
    pieces = [np.zeros((2, TRIM), np.float32)]  # the same leading pad as separate()
    have = TRIM
    n = written = 0

    def flush(buf: np.ndarray, count: int) -> np.ndarray:
        nonlocal written
        outs = _run_chunks(session, in_name, [buf[:, k * GEN : k * GEN + CHUNK] for k in range(count)])
        for k, out in enumerate(outs):
            mix = buf[:, k * GEN + TRIM : k * GEN + TRIM + GEN]
            keep = max(0, min(GEN, n_final - written)) if n_final is not None else GEN
            if keep:
                write(out[:, :keep], mix[:, :keep])
                written += keep
        if total:
            emit({"progress": round(min(1.0, written / total), 3)})
        return buf[:, count * GEN :]

    n_final = None
    need = batch * GEN + 2 * TRIM
    for f in frames:
        pieces.append(f.astype(np.float32, copy=False))
        have += f.shape[1]
        n += f.shape[1]
        if have >= need:
            buf = np.concatenate(pieces, axis=1)
            while buf.shape[1] >= need:
                buf = flush(buf, batch)
            pieces, have = [buf], buf.shape[1]
    n_final = n
    pad_end = GEN - n % GEN
    buf = np.concatenate(pieces + [np.zeros((2, pad_end + TRIM), np.float32)], axis=1)
    while buf.shape[1] >= CHUNK:
        buf = flush(buf, min(batch, (buf.shape[1] - 2 * TRIM) // GEN))
    return n


def stereo_frames(path: str):
    """Decode any video/audio to float32 [2, k] pieces at 44.1 kHz, as it is read."""
    import av

    res = av.audio.resampler.AudioResampler(format="fltp", layout="stereo", rate=SR)
    with av.open(path) as c:
        for frame in c.decode(audio=0):
            for f in res.resample(frame):
                yield f.to_ndarray()
        for f in res.resample(None):
            yield f.to_ndarray()


def duration_samples(path: str) -> int:
    try:
        import av

        with av.open(path) as c:
            return int((c.duration or 0) / 1_000_000 * SR)
    except Exception:  # noqa: BLE001 — only used for the progress bar
        return 0


class WavWriter:
    """Appends stereo float audio to a 16-bit WAV file."""

    def __init__(self, path: str):
        self.w = wave.open(path, "wb")
        self.w.setnchannels(2)
        self.w.setsampwidth(2)
        self.w.setframerate(SR)

    def write(self, audio: np.ndarray) -> None:
        self.w.writeframes((np.clip(audio.T, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes())

    def close(self) -> None:
        self.w.close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vocals-out", default=None, help="optional: the speech alone (for testing)")
    args = ap.parse_args(argv)

    import onnxruntime as ort

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = os.cpu_count() or 4
    session = ort.InferenceSession(args.model, sess_options=opts, providers=["CPUExecutionProvider"])
    out = WavWriter(args.out)
    vocals = WavWriter(args.vocals_out) if args.vocals_out else None

    def write(background: np.ndarray, mix: np.ndarray) -> None:
        out.write(background)
        if vocals:
            vocals.write(mix - background)

    try:
        n = separate_stream(session, stereo_frames(args.input), write, total=duration_samples(args.input))
    finally:
        out.close()
        if vocals:
            vocals.close()
    if not n:
        raise SystemExit("NO_AUDIO")
    emit({"ok": True, "out": args.out, "seconds": round(n / SR, 2)})


if __name__ == "__main__":
    main()
