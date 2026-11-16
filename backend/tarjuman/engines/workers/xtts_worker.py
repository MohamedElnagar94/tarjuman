"""Runs inside the XTTS voice pack's own Python (data/engines/xtts/venv), never inside Tarjuman's.

One JSON request per line on stdin, one JSON answer per line on stdout:
    {"cmd": "synth", "text": "...", "lang": "ar", "ref": "speaker.wav", "out": "seg.wav", "speed": 1.0}
    -> {"ok": true, "duration": 3.2}      or      {"ok": false, "error": "..."}
The model loads with the first request and stays loaded until stdin closes."""

import json
import os
import sys

# Installed with --target when Tarjuman's Python has no venv (the Windows installer): load from there first.
if os.environ.get("TARJUMAN_PACK_SITE"):
    sys.path.insert(0, os.environ["TARJUMAN_PACK_SITE"])

# COQUI_TOS_AGREED comes from Tarjuman, which sets it only after the user accepted the CPML licence.

# Coqui maps XTTS's language codes like this; everything else is passed as it is.
LANG = {"zh": "zh-cn"}
SUPPORTED = {"en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hu", "ko", "hi"}

_tts = None


def _load():
    global _tts
    if _tts is None:
        import soundfile as sf
        import torch
        import torchaudio

        # torchaudio reads audio through torchcodec, which needs FFmpeg DLLs Windows doesn't ship: soundfile instead.
        def _read(path, *a, **k):
            data, sr = sf.read(path, dtype="float32", always_2d=True)
            return torch.from_numpy(data.T.copy()), sr

        torchaudio.load = _read
        torch.set_num_threads(max(1, min(8, os.cpu_count() or 4)))
        from TTS.api import TTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    return _tts


def synth(req: dict) -> dict:
    import soundfile as sf

    lang = req.get("lang") or "en"
    if lang not in SUPPORTED:
        return {"ok": False, "error": "LANG_NOT_SUPPORTED"}
    tts = _load()
    speed = min(2.0, max(0.5, float(req.get("speed") or 1.0)))
    wav = tts.tts(text=req["text"], speaker_wav=req["ref"], language=LANG.get(lang, lang), speed=speed)
    sf.write(req["out"], wav, 24000, subtype="PCM_16")
    return {"ok": True, "duration": round(len(wav) / 24000, 3)}


def main() -> None:
    # Answers go to the real stdout; everything the libraries print (download notes, progress) goes to
    # stderr, so it can never be mistaken for an answer.
    answers = sys.stdout
    sys.stdout = sys.stderr
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = {"ok": True} if req.get("cmd") == "ping" else synth(req)
        except Exception as e:  # noqa: BLE001 — reported back, the worker keeps serving
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        answers.write(json.dumps(res) + "\n")
        answers.flush()


if __name__ == "__main__":
    main()
