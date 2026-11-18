"""The first run imports the command line before `setup` has installed any package."""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

# Run in a fresh interpreter in which the backend's packages can't be imported, as in a new venv.
BLOCKED = ("httpx", "fastapi", "uvicorn", "anthropic", "edge_tts", "faster_whisper", "piper", "yt_dlp", "numpy", "av")


def test_command_line_starts_without_the_packages_setup_installs():
    code = (
        "import sys\n"
        f"for name in {BLOCKED!r}: sys.modules[name] = None\n"
        "from tarjuman.__main__ import main\n"
        "main(['--version'])\n"
    )
    res = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip()
