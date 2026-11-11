"""Paths, ports and environment settings. Everything the app writes lives under ``data/``."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env_file(path: Path) -> dict[str, str]:
    """Settings from a ``.env`` file (``NAME=value`` lines, ``#`` comments). A variable already set
    in the real environment wins over the file. Returns what the file set."""
    applied: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return applied
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        if name and name not in os.environ:
            os.environ[name] = applied[name] = value
    return applied


if os.environ.get("TARJUMAN_NO_ENV_FILE") != "1":
    load_env_file(PROJECT_ROOT / ".env")


def _number(name: str, default: float) -> float:
    """A numeric setting; a value that isn't a number falls back to the default instead of stopping the app."""
    try:
        return float(os.environ.get(name) or default)
    except ValueError:
        print(f"  {name}={os.environ.get(name)!r} is not a number; using {default:g}", file=sys.stderr)
        return default


def _default_home() -> Path:
    # The installed Windows app (marked by installed.txt) keeps the user's data apart from the program,
    # so an update or a reinstall never touches it.
    local = os.environ.get("LOCALAPPDATA")
    if local and (PROJECT_ROOT / "installed.txt").exists():
        return Path(local) / "Tarjuman"
    return PROJECT_ROOT


HOME = Path(os.environ.get("TARJUMAN_HOME") or _default_home())
# The installed app keeps the user's .env next to their data, away from the program folder.
if HOME != PROJECT_ROOT and os.environ.get("TARJUMAN_NO_ENV_FILE") != "1":
    load_env_file(HOME / ".env")
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

DEFAULT_PORT = int(_number("TARJUMAN_PORT", 4318))
PORT_TRIES = 10
DEFAULT_HOST = os.environ.get("TARJUMAN_HOST") or "0.0.0.0"

WHISPER_MODEL = os.environ.get("TARJUMAN_WHISPER_MODEL") or "base"

# Uploads: at most this big, and never leaving less than DISK_RESERVE_BYTES free on the disk.
MAX_UPLOAD_BYTES = int(_number("TARJUMAN_MAX_UPLOAD_GB", 8) * (1 << 30))
DISK_RESERVE_BYTES = 1 << 30
# The voice clip cache (data/cache/tts) is kept under this size, least recently used clips first.
VOICE_CACHE_BYTES = int(_number("TARJUMAN_VOICE_CACHE_GB", 2) * 1e9)
FORCE_ASR = os.environ.get("TARJUMAN_FORCE_ASR") == "1"
# The pairing code (the QR) is replaced after this many minutes; 0 keeps it until a new one is asked for.
PAIR_CODE_MINUTES = _number("TARJUMAN_PAIR_MINUTES", 15)
# Downloading from addresses inside the local network (a home media server) is off unless asked for.
FETCH_PRIVATE = os.environ.get("TARJUMAN_FETCH_PRIVATE") == "1"
# Whisper, dubbing and burning subtitles are heavy: this many of them run at once, whatever their kinds.
HEAVY_JOBS = max(1, int(_number("TARJUMAN_HEAVY_JOBS", 2)))
# Jobs waiting for their turn; a new one is refused beyond this.
MAX_QUEUE = max(1, int(_number("TARJUMAN_MAX_QUEUE", 20)))

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
