"""Paths, ports and environment settings. Everything the app writes lives under ``data/``."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOME = Path(os.environ.get("TARJUMAN_HOME") or PROJECT_ROOT)
DATA = HOME / "data"

CACHE = DATA / "cache"
TTS_DIR = CACHE / "tts"
OUTPUT = DATA / "output"
DUBBED = OUTPUT / "dubbed"
MEDIA_DIR = OUTPUT / "media"
MODELS = DATA / "models"
TMP = DATA / "tmp"

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
DUB_ENGINE_JS = PROJECT_ROOT / "shared" / "dub-engine" / "src" / "index.js"
ICON_SVG = PROJECT_ROOT / "assets" / "brand" / "icon.svg"
REQUIREMENTS = PROJECT_ROOT / "backend" / "requirements.txt"

DEFAULT_PORT = int(os.environ.get("TARJUMAN_PORT") or 4318)
PORT_TRIES = 10
DEFAULT_HOST = os.environ.get("TARJUMAN_HOST") or "0.0.0.0"

WHISPER_MODEL = os.environ.get("TARJUMAN_WHISPER_MODEL") or "base"

# Uploads: at most this big, and never leaving less than DISK_RESERVE_BYTES free on the disk.
MAX_UPLOAD_BYTES = int(float(os.environ.get("TARJUMAN_MAX_UPLOAD_GB") or 8) * (1 << 30))
DISK_RESERVE_BYTES = 1 << 30
# The voice clip cache (data/cache/tts) is kept under this size, least recently used clips first.
VOICE_CACHE_BYTES = int(float(os.environ.get("TARJUMAN_VOICE_CACHE_GB") or 2) * 1e9)
FORCE_ASR = os.environ.get("TARJUMAN_FORCE_ASR") == "1"

PIPER_VOICE = "ar_JO-kareem-medium"
PIPER_MODEL = MODELS / "piper" / f"{PIPER_VOICE}.onnx"
PIPER_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium/" + PIPER_VOICE

SEP_MODEL = MODELS / "UVR-MDX-NET-Inst_HQ_3.onnx"
SEP_MODEL_URL = (
    "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/UVR-MDX-NET-Inst_HQ_3.onnx"
)

HF_HOME = MODELS / "hf"

PYTHON = sys.executable
IS_WIN = sys.platform == "win32"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def ensure_dirs() -> None:
    for d in (CACHE, TTS_DIR, OUTPUT, DUBBED, MEDIA_DIR, MODELS, TMP):
        d.mkdir(parents=True, exist_ok=True)


def child_env(**extra: str) -> dict[str, str]:
    """Environment for Python subprocesses (mixer, separator, yt-dlp)."""
    env = dict(os.environ)
    env.update(
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        PYTHONUNBUFFERED="1",
        HF_HOME=str(HF_HOME),
        HF_HUB_DISABLE_SYMLINKS_WARNING="1",
        PYTHONPATH=os.pathsep.join(filter(None, [str(PROJECT_ROOT / "backend"), env.get("PYTHONPATH", "")])),
    )
    env.update(extra)
    return env


# Whisper (faster-whisper / huggingface_hub) reads this at import time.
os.environ.setdefault("HF_HOME", str(HF_HOME))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
