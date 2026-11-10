"""Build the dubbed audio track and mux it with the video.

    python -m tarjuman.media.mixer --segments segs.json --video in.mp4 --wav-out mix.wav --mp4-out out.mp4
        [--duration S] [--pitch 1.0] [--match-voice] [--bg-volume 0.15] [--bg-audio background.wav]
        [--subs subs.srt --sub-lang ar [--burn-subs]]

Each segment is {"audio": wav, "at"|"start": seconds, "room"|"slot": seconds}. Sentences never overlap:
if the previous one is still talking we wait briefly, otherwise it is faded out. The original audio
(or the separated background, with the speaker removed) sits under the dub and ducks while it speaks.
Prints one JSON line with what happened.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave

import numpy as np

from .pitch import estimate_f0, pcm_from_video

# Burned subtitles: a font with Arabic shaping, a translucent box, size relative to the video height.
BURN_STYLE = "FontName=Arial,FontSize=17,BorderStyle=3,Outline=1,Shadow=0,BackColour=&H90000000,MarginV=24"
LANG3 = {"ar": "ara", "en": "eng", "fr": "fra", "es": "spa", "de": "deu", "tr": "tur"}
MAX_TEMPO = 1.25


def read_wav(path: str) -> tuple[int, np.ndarray]:
    with wave.open(path, "rb") as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        frames = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError("WAV must be 16-bit: " + path)
    data = np.frombuffer(frames, dtype=np.int16)
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1).astype(np.int16)
    return rate, data


def video_has_audio(path: str) -> bool:
    try:
        import av

        with av.open(path) as c:
            return any(s.type == "audio" for s in c.streams)
    except Exception:  # noqa: BLE001
        return False


def process_segment(ffmpeg: str, src: str, dst: str, rate: int, pitch: float, tempo: float) -> None:
    filters = []
    if abs(pitch - 1.0) > 0.02:
        filters += [f"asetrate={round(rate * pitch)}", f"aresample={rate}", f"atempo={1.0 / pitch:.6f}"]
    if tempo > 1.001:
        filters.append(f"atempo={min(tempo, 2.0):.6f}")
    if not filters:
        if os.path.abspath(src) != os.path.abspath(dst):
            os.replace(src, dst)
        return
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", src, "-filter:a", ",".join(filters), "-ar", str(rate), "-ac", "1", dst], capture_output=True
    )
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg segment failed: " + proc.stderr.decode("utf-8", "ignore")[-300:])
    try:
        os.unlink(src)
    except OSError:
        pass


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--wav-out", required=True)
    ap.add_argument("--mp4-out", required=True)
    ap.add_argument("--rate", type=int, default=22050)
    ap.add_argument("--duration", type=float, default=0.0)
    ap.add_argument("--pitch", type=float, default=1.0, help="fixed pitch (1.0 = natural)")
    ap.add_argument("--match-voice", action="store_true", help="match the original speaker's pitch")
    ap.add_argument("--bg-volume", type=float, default=0.0, help="original audio under the dub (0 = none)")
    ap.add_argument("--subs", default=None, help="SRT to add as a subtitle track")
    ap.add_argument("--sub-lang", default="ar")
    ap.add_argument("--burn-subs", action="store_true", help="burn the subtitles into the picture")
    ap.add_argument("--bg-audio", default=None, help="background without the speaker (from the separator)")
    args = ap.parse_args(argv)

    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    rate = args.rate
    with open(args.segments, "r", encoding="utf-8-sig") as fh:
        segs = json.load(fh)
    duration = args.duration
    if duration <= 0 and segs:
        duration = max(s["start"] for s in segs) + 10.0

    pitch = float(args.pitch or 1.0)
    voice_note = "natural"
    if args.match_voice and segs:
        try:
            speaker_f0 = estimate_f0(pcm_from_video(args.video, 16000, 120.0), 16000)
            first_audio = next((s["audio"] for s in segs if os.path.exists(s.get("audio", ""))), None)
            tts_f0 = 0.0
            if first_audio:
                r, d = read_wav(first_audio)
                tts_f0 = estimate_f0(d, r)
            if 60 < speaker_f0 < 400 and 60 < tts_f0 < 400:
                pitch = float(np.clip(speaker_f0 / tts_f0, 0.82, 1.22))
                voice_note = f"matched(speaker={speaker_f0:.0f}Hz tts={tts_f0:.0f}Hz)"
        except Exception as e:  # noqa: BLE001
            print("match-voice failed:", e, file=sys.stderr)

    # float32: a two-hour track is ~635 MB instead of 1.3 GB, with no audible difference.
    buf = np.zeros(int(duration * rate) + rate, dtype=np.float32)
    placed = compressed = trimmed = delayed = 0
    last_end = 0
    for i, s in enumerate(segs):
        path = s.get("audio")
        if not path or not os.path.exists(path):
            continue
        start_s = float(s.get("at", s.get("start", 0)))
        if s.get("room"):
            slot = float(s["room"])  # scheduled exactly by the dub job
        elif s.get("slot"):
            slot = float(s["slot"]) + 0.15
        else:
            nxt = next((float(x["start"]) for x in segs[i + 1 :] if x.get("start") is not None), None)
            slot = max(0.6, nxt - start_s + 0.35) if nxt is not None else None
        try:
            sr, data = read_wav(path)
        except Exception as e:  # noqa: BLE001
            print("skip", path, e, file=sys.stderr)
            continue
        dur = len(data) / float(sr)
        tempo = 1.0
        if slot is not None and dur > slot * 1.02:
            # The clip was already made at the right speed; this is only a small final adjustment.
            tempo = min(dur / slot, MAX_TEMPO)
            compressed += 1
        out_path = path + ".p.wav"
        try:
            process_segment(ffmpeg, path, out_path, sr, pitch, tempo)
            hr, hdata = read_wav(out_path)
        except Exception as e:  # noqa: BLE001
            print("process failed", path, e, file=sys.stderr)
            hr, hdata = read_wav(path)
        if hr != rate:
            n_out = int(round(len(hdata) * rate / hr))
            x_old = np.arange(len(hdata), dtype=np.float64)
            x_new = np.linspace(0, len(hdata) - 1, max(1, n_out))
            hdata = np.interp(x_new, x_old, hdata.astype(np.float64)).astype(np.int16)

        start_sample = max(0, int(round(start_s * rate)))
        chunk = hdata.astype(np.float32) / 32768.0
        # Never two voices at once: wait briefly for the previous sentence, or fade it out.
        if start_sample < last_end:
            if (last_end - start_sample) / rate <= 0.8:
                start_sample = last_end + int(0.05 * rate)
                delayed += 1
            else:
                fade = min(int(0.12 * rate), start_sample)
                buf[start_sample - fade : start_sample] *= np.linspace(1.0, 0.0, fade)
                buf[start_sample:last_end] = 0.0
        if slot is not None:
            max_samples = int(slot * rate)
            if len(chunk) > max_samples:
                trimmed += 1
                chunk = chunk[:max_samples].copy()
                fade = min(int(0.08 * rate), len(chunk))
                if fade > 0:
                    chunk[-fade:] *= np.linspace(1.0, 0.0, fade)
        end = start_sample + len(chunk)
        if end > len(buf):
            buf = np.concatenate([buf, np.zeros(end - len(buf) + rate, dtype=np.float32)])
        buf[start_sample:end] += chunk
        last_end = end
        placed += 1

    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.99:
        buf *= 0.99 / peak
    pcm16 = (np.clip(buf, -1.0, 1.0) * 32767.0).astype(np.int16)
    os.makedirs(os.path.dirname(os.path.abspath(args.wav_out)), exist_ok=True)
    with wave.open(args.wav_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm16.tobytes())

    bg_volume = max(0.0, min(1.0, args.bg_volume))
    has_audio = video_has_audio(args.video)
    has_subs = bool(args.subs and os.path.exists(args.subs))
    burn = has_subs and args.burn_subs
    clean_bg = bool(args.bg_audio and os.path.exists(args.bg_audio))
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", args.video, "-i", args.wav_out]
    if clean_bg:
        cmd += ["-i", args.bg_audio]
    subs_index = 3 if clean_bg else 2
    if has_subs and not burn:
        cmd += ["-i", args.subs]

    # The dub is padded with silence to the end of the video (apad + -shortest) so the video is not cut.
    if bg_volume > 0 and (has_audio or clean_bg):
        # Like real dubbing: the original rises in pauses and dips under speech (sidechain). With the
        # speaker removed, music and effects can stay much louder (no English competing).
        bg_level = min(1.0, bg_volume * (5.0 if clean_bg else 2.2))
        bg_src = "[2:a:0]" if clean_bg else "[0:a:0]"
        filters = (
            f"{bg_src}aformat=channel_layouts=mono,volume={bg_level:.3f}[bg];"
            "[1:a:0]apad,asplit=2[dub][key];"
            "[bg][key]sidechaincompress=threshold=0.015:ratio=12:attack=15:release=450:makeup=1[duck];"
            "[duck][dub]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]"
        )
    else:
        filters = "[1:a:0]apad[aout]"
    if burn:
        # libass shapes Arabic correctly. The path is relative: ffmpeg runs from the subtitle's folder.
        filters += f";[0:v:0]subtitles={os.path.basename(args.subs)}:force_style='{BURN_STYLE}'[vout]"
        cmd += ["-filter_complex", filters, "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-filter_complex", filters, "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy"]
        if has_subs:
            cmd += ["-map", f"{subs_index}:s:0", "-c:s", "mov_text",
                    "-metadata:s:s:0", f"language={LANG3.get(args.sub_lang, args.sub_lang)}"]
    cmd += ["-c:a", "aac", "-b:a", "160k", "-metadata:s:a:0", f"language={LANG3.get(args.sub_lang, args.sub_lang)}",
            "-shortest", "-movflags", "+faststart", args.mp4_out]
    proc = subprocess.run(cmd, capture_output=True, cwd=os.path.dirname(os.path.abspath(args.subs)) if burn else None)
    if proc.returncode != 0:
        raise SystemExit("ffmpeg mux failed: " + proc.stderr.decode("utf-8", "ignore")[-600:])

    print(json.dumps({
        "ok": True, "placed": placed, "segments": len(segs), "compressed": compressed, "trimmed": trimmed,
        "delayed": delayed, "pitch": round(pitch, 3), "voice": voice_note,
        "bgVolume": bg_volume if (has_audio or clean_bg) else 0, "voiceRemoved": clean_bg,
        "subs": bool(args.subs), "mp4": args.mp4_out, "size": os.path.getsize(args.mp4_out),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
