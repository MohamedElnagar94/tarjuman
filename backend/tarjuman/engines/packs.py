"""Optional voice packs that need PyTorch, too big for the installer (one to several GB each).

A pack is installed from Settings into data/engines/<name>: its own Python environment (created with
Tarjuman's Python), the exact package versions tested on 14 Nov 2026, and its model. Tarjuman talks to it
through a small worker script (engines/workers) that runs in that environment, one JSON line per sentence,
so a broken or half-installed pack can never break the app itself.

- xtts:   speaks a dubbed MP4 in the original speaker's voice, in 17 languages (Coqui XTTS-v2, CPML licence:
          non-commercial use; the user accepts it before installing). About 3.5x slower than real time on a
          2016 laptop CPU, so MP4 export only.
- habibi: Arabic dialect voices (Egyptian, Iraqi, Moroccan, Algerian, MSA; the Apache-2.0 models only).
          40-110x slower than real time on that CPU: offered when the computer has a capable NVIDIA card."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ..core.errors import AppError
from ..core.store import read_json, write_json

log = logging.getLogger("tarjuman.packs")
WORKERS = Path(__file__).with_name("workers")
CPU_INDEX = "https://download.pytorch.org/whl/cpu"
CUDA_INDEX = "https://download.pytorch.org/whl/cu128"

PACKS: dict[str, dict] = {
    "xtts": {
        "torch": ["torch==2.11.*", "torchaudio==2.11.1"],
        "packages": ["coqui-tts[codec]==0.28.0", "six", "soundfile"],
        "worker": "xtts_worker.py",
        "licence": "CPML",
        "sizeGb": 4.5,
        "langs": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh", "ja", "hu", "ko", "hi"],
        "needsGpu": False,
    },
    "habibi": {
        "torch": ["torch==2.8.0", "torchaudio==2.8.0"],
        "packages": ["habibi-tts==0.1.1", "soundfile"],
        "worker": "habibi_worker.py",
        "licence": "Apache-2.0",
        "sizeGb": 6.0,
        "langs": ["ar"],
        "needsGpu": True,
    },
}

# Reference voices for Habibi's dialects: the clips shipped with the habibi-tts package and their words.
HABIBI_REFS = {
    "EGY": ("EGY.mp3", "ايه الكلام. بقولك ايه. استخدم صوتي في المحادثات. استخدمه هيعجبك اوي."),
    "IRQ": ("IRQ.wav", "يعني ااا ما نقدر ناخذ وقت أكثر، ااا لأنه شروط كلش يحتاجلها وقت."),
    "MAR": ("MAR.mp3", "إذا بغيتي شي صوت باللهجة المغربية للإعلانات ديالك هذا أحسن واحد غادي تلقاه."),
    "ALG": ("ALG.wav", "أنيا هكا باغية ناكل هكا أني ن نشوف فيها الحاجة هذيكا."),
    "MSA": ("MSA.mp3", "كان اللعيب حاضرًا في العديد من الأنشطة والفعاليات المرتبطة بكأس العالم، مما سمح للجماهير بالتفاعل معه والتقاط الصور التذكارية."),
}


def base_python() -> str:
    """Tarjuman's Python as a console program (pythonw.exe can't run pip with visible output)."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and (exe.parent / "python.exe").exists():
        return str(exe.parent / "python.exe")
    return str(exe)


def strong_gpu(hw: dict) -> bool:
    """A card these models run well on: NVIDIA, CUDA usable, compute capability 7.0+, 6 GB or more."""
    return bool(hw.get("cuda")) and float(hw.get("computeCap") or 0) >= 7.0 and float(hw.get("vramGb") or 0) >= 6


class Pack:
    def __init__(self, name: str, root: Path):
        self.name = name
        self.spec = PACKS[name]
        self.dir = root / name
        self.state: dict = {"status": "idle", "phase": "", "error": "", "log": ""}
        self._proc: subprocess.Popen | None = None
        self._lock = asyncio.Lock()

    @property
    def python(self) -> Path:
        v = self.dir / "venv"
        return v / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    @property
    def installed(self) -> bool:
        return (self.dir / "ready.json").exists() and self.python.exists()

    def info(self) -> dict:
        return {
            "name": self.name,
            "installed": self.installed,
            "licence": self.spec["licence"],
            "sizeGb": self.spec["sizeGb"],
            "langs": self.spec["langs"],
            "needsGpu": self.spec["needsGpu"],
            "accepted": self.accepted,
            **self.state,
        }

    # ---------------- install ----------------

    @property
    def accepted(self) -> bool:
        return self.spec["licence"] != "CPML" or (self.dir / "licence-accepted.json").exists()

    def accept(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        write_json(self.dir / "licence-accepted.json", {"licence": self.spec["licence"]})

    async def install(self, gpu: bool) -> None:
        if self.state["status"] == "working" or self.installed:
            return
        if not self.accepted:
            raise AppError("LICENCE_NOT_ACCEPTED")
        self.state = {"status": "working", "phase": "venv", "error": "", "log": ""}
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            if not self.python.exists():
                await self._run([base_python(), "-m", "venv", str(self.dir / "venv")])
            self.state["phase"] = "packages"
            await self._run([str(self.python), "-m", "pip", "install", "--upgrade", "pip"])
            await self._run([str(self.python), "-m", "pip", "install", *self.spec["torch"], "--index-url", CUDA_INDEX if gpu else CPU_INDEX])
            await self._run([str(self.python), "-m", "pip", "install", *self.spec["packages"]])
            if self.name == "habibi":
                self.state["phase"] = "voices"
                await asyncio.to_thread(self._prepare_habibi_refs)
            self.state["phase"] = "model"
            await self._warm()
            write_json(self.dir / "ready.json", {"gpu": gpu, "torch": self.spec["torch"], "packages": self.spec["packages"]})
            self.state = {"status": "done", "phase": "", "error": "", "log": ""}
        except Exception as e:  # noqa: BLE001 — shown in Settings; the pack folder stays for a retry
            log.warning("voice pack %s failed: %r", self.name, e)
            self.state.update(status="error", error=str(getattr(e, "code", "") or "INSTALL_FAILED"))

    async def _run(self, cmd: list[str]) -> None:
        env = {**os.environ, **self._env()}
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, env=env)
        tail: list[str] = []
        assert proc.stdout
        async for raw in proc.stdout:
            line = raw.decode("utf-8", "replace").rstrip()
            if line:
                tail = (tail + [line])[-20:]
                self.state["log"] = line[-160:]
        if await proc.wait() != 0:
            log.warning("pack %s: %s failed:\n%s", self.name, cmd[2:4], "\n".join(tail))
            raise AppError("INSTALL_FAILED", "\n".join(tail[-3:]))

    def _env(self) -> dict:
        env = {"HF_HOME": str(self.dir / "hf"), "TTS_HOME": str(self.dir / "models"), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        if self.spec["licence"] == "CPML" and self.accepted:
            env["COQUI_TOS_AGREED"] = "1"  # the user accepted Coqui's non-commercial licence in Settings
        return env

    def _prepare_habibi_refs(self) -> None:
        """The dialect clips as 24 kHz WAV (the pack has no FFmpeg of its own), with their transcripts."""
        from ..media.ffmpeg import ffmpeg_exe

        site = subprocess.run([str(self.python), "-c", "import habibi_tts, os; print(os.path.dirname(habibi_tts.__path__[0] if hasattr(habibi_tts, '__path__') else habibi_tts.__file__))"],
                              capture_output=True, text=True, check=True).stdout.strip()
        assets = Path(site) / "habibi_tts" / "assets"
        refs = self.dir / "refs"
        refs.mkdir(parents=True, exist_ok=True)
        for dialect, (name, text) in HABIBI_REFS.items():
            subprocess.run([ffmpeg_exe(), "-loglevel", "error", "-y", "-i", str(assets / name), "-ac", "1", "-ar", "24000", str(refs / f"{dialect}.wav")], check=True)
        write_json(refs / "refs.json", {d: t for d, (_, t) in HABIBI_REFS.items()})

    async def _warm(self) -> None:
        """Downloads the model by saying one short sentence."""
        out = self.dir / "warm.wav"
        if self.name == "xtts":
            ref = self.dir / "warm_ref.wav"
            await asyncio.to_thread(_tone, ref)
            try:
                await self.synth({"text": "Hello.", "lang": "en", "ref": str(ref), "out": str(out)})
            finally:
                ref.unlink(missing_ok=True)
        else:
            refs = read_json(self.dir / "refs" / "refs.json", {})
            await self.synth({"text": "أهلًا.", "dialect": "EGY", "ref": str(self.dir / "refs" / "EGY.wav"), "ref_text": refs.get("EGY", ""), "out": str(out)})
        out.unlink(missing_ok=True)

    def delete(self) -> None:
        self.stop()
        shutil.rmtree(self.dir, ignore_errors=True)
        self.state = {"status": "idle", "phase": "", "error": "", "log": ""}

    # ---------------- speaking ----------------

    def _start(self) -> subprocess.Popen:
        if self._proc and self._proc.poll() is None:
            return self._proc
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            [str(self.python), str(WORKERS / self.spec["worker"])],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={**os.environ, **self._env()}, text=True, encoding="utf-8", bufsize=1, creationflags=flags,
        )
        return self._proc

    def _ask(self, req: dict) -> dict:
        p = self._start()
        assert p.stdin and p.stdout
        p.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        p.stdin.flush()
        line = p.stdout.readline()
        if not line:
            raise AppError("PACK_STOPPED")
        return json.loads(line)

    async def synth(self, req: dict) -> float:
        """Writes the sentence to req["out"] (WAV) and returns its length in seconds."""
        async with self._lock:
            res = await asyncio.to_thread(self._ask, {"cmd": "synth", **req})
        if not res.get("ok"):
            raise AppError("PACK_FAILED", str(res.get("error") or ""))
        return float(res.get("duration") or 0)

    def refs(self) -> dict:
        return read_json(self.dir / "refs" / "refs.json", {})

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.close()  # type: ignore[union-attr]
                self._proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                self._proc.kill()
        self._proc = None


def _tone(path: Path) -> None:
    """A second of a soft tone: enough for XTTS to load and download its model, not to clone anyone."""
    import math
    import wave

    rate = 24000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(int(3000 * math.sin(2 * math.pi * 180 * i / rate)).to_bytes(2, "little", signed=True) for i in range(rate * 2)))


class Packs:
    def __init__(self, root: Path):
        self.root = root
        self.items = {name: Pack(name, root) for name in PACKS}

    def get(self, name: str) -> Pack:
        if name not in self.items:
            raise AppError("NOT_FOUND")
        return self.items[name]

    def status(self, hw: dict) -> dict:
        return {"strongGpu": strong_gpu(hw), "packs": [p.info() for p in self.items.values()]}

    def stop_all(self) -> None:
        for p in self.items.values():
            p.stop()
