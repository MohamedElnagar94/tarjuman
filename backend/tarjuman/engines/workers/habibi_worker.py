"""Runs inside the Habibi voice pack's own Python (data/engines/habibi/venv), never inside Tarjuman's.

Habibi (SJTU, F5-TTS based) speaks Arabic dialects. Only the dialect models released under Apache-2.0 are
used: Egyptian, Iraqi, Moroccan, Algerian and Modern Standard Arabic (the Saudi, Emirati and unified models
are non-commercial). Each voice is cloned from a short reference clip with its transcript.

One JSON request per line on stdin, one JSON answer per line on stdout:
    {"cmd": "synth", "text": "...", "dialect": "EGY", "ref": "ref.wav", "ref_text": "...", "out": "seg.wav", "speed": 1.0}
    -> {"ok": true, "duration": 3.2}"""

import json
import os
import sys

DIALECTS = {"EGY": 100000, "IRQ": 100000, "MAR": 100000, "ALG": 100000, "MSA": 200000}
_models: dict = {}
_vocoder = None


def _load(dialect: str):
    global _vocoder
    import torch
    from cached_path import cached_path
    from f5_tts.infer.utils_infer import load_model, load_vocoder
    from hydra.utils import get_class
    from importlib.resources import files
    from omegaconf import OmegaConf

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 4)))
    cfg = OmegaConf.load(str(files("f5_tts").joinpath("configs/F5TTS_v1_Base.yaml")))
    if dialect not in _models:
        step = DIALECTS[dialect]
        ckpt = str(cached_path(f"hf://SWivid/Habibi-TTS/Specialized/{dialect}/model_{step}.safetensors"))
        vocab = str(cached_path(f"hf://SWivid/Habibi-TTS/Specialized/{dialect}/vocab.txt"))
        cls = get_class(f"f5_tts.model.{cfg.model.backbone}")
        _models[dialect] = load_model(cls, cfg.model.arch, ckpt, mel_spec_type=cfg.model.mel_spec.mel_spec_type, vocab_file=vocab, device=device)
    if _vocoder is None:
        _vocoder = load_vocoder(vocoder_name=cfg.model.mel_spec.mel_spec_type, device=device)
    return _models[dialect], _vocoder, cfg.model.mel_spec.mel_spec_type, device


def synth(req: dict) -> dict:
    import soundfile as sf
    from f5_tts.infer.utils_infer import preprocess_ref_audio_text
    from habibi_tts.infer.utils_infer import infer_process

    dialect = req.get("dialect") or "MSA"
    if dialect not in DIALECTS:
        return {"ok": False, "error": "DIALECT_NOT_FREE"}
    model, vocoder, mel, device = _load(dialect)
    ref_a, ref_t = preprocess_ref_audio_text(req["ref"], req.get("ref_text") or "")
    wav, sr, _ = infer_process(ref_a, ref_t, req["text"], model, vocoder, mel_spec_type=mel, device=device,
                               speed=min(2.0, max(0.5, float(req.get("speed") or 1.0))))
    sf.write(req["out"], wav, sr, subtype="PCM_16")
    return {"ok": True, "duration": round(len(wav) / sr, 3)}


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
        except Exception as e:  # noqa: BLE001
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        answers.write(json.dumps(res) + "\n")
        answers.flush()


if __name__ == "__main__":
    main()
