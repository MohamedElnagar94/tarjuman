"""Command line: serve the app, export subtitles, set up or check the environment.

    python -m tarjuman                      start the app (opens the browser)
    python -m tarjuman subs <link>          write subtitle files to data/output
    python -m tarjuman setup                install everything (Python packages, Piper voice, web app)
    python -m tarjuman update               update yt-dlp and edge-tts (if downloads stop working)
    python -m tarjuman doctor               check every component
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from . import __version__, config
from .core.net import lan_ip


def _free_port(host: str, start: int) -> int:
    for p in range(start, start + config.PORT_TRIES):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host if host != "0.0.0.0" else "", p))
                return p
            except OSError:
                continue
    raise SystemExit(f"No free port between {start} and {start + config.PORT_TRIES - 1}")


def serve(args: argparse.Namespace) -> None:
    import uvicorn

    from .api.app import create_app

    host = args.host
    port = _free_port(host, args.port)
    app = create_app(port=port)
    local = f"http://127.0.0.1:{port}"
    print(f"\n  Tarjuman {__version__}")
    print(f"  Open: {local}")
    if host == "0.0.0.0":
        ip = lan_ip()
        if ip:
            # Opening this link once pairs the phone (the code is also shown as a QR in Settings → Phone).
            life = f" (valid for {config.PAIR_CODE_MINUTES:g} minutes; later, use the QR in Settings)" if config.PAIR_CODE_MINUTES > 0 else ""
            print(f"  From your phone (same Wi-Fi), open once: http://{ip}:{port}/pair?code={app.state.pairing.current_code()}{life}")
    if port != args.port:
        print(f"  Port {args.port} was busy; the extension finds the new port on its own.")
    if not config.FRONTEND_DIST.joinpath("index.html").exists():
        print("  The web app isn't built yet: npm --prefix frontend install && npm --prefix frontend run build")
    print("  Stop: Ctrl + C\n")
    if not args.no_open:
        threading.Timer(1.2, lambda: webbrowser.open(local)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")


def desktop(args: argparse.Namespace) -> None:
    from . import desktop as d

    d.run(args.host, args.port, _free_port)


def subs(args: argparse.Namespace) -> None:
    from .captions.formats import SUB_FORMATS
    from .core import http
    from .core.text import safe_name
    from .services import Services

    async def run() -> None:
        s = Services()
        s.load()
        out = config.OUTPUT
        t0 = time.time()
        print("\n  Fetching captions…")
        data = await s.captions.get(args.link, args.lang)
        print(f"  {data.title}\n  {len(data.cues)} lines")
        if not data.alreadyTranslated:
            print(f"  Translating {data.srcLang} → {args.lang}…")
            await s.translator.translate_cues(
                data.cues, tl=args.lang, sl=data.srcLang or "auto",
                on_progress=lambda d, t: print(f"   {d * 100 // max(t, 1)}% ({d}/{t})", end="\r"),
            )
            print()
        base = safe_name(data.title)
        written = []
        for fmt in [f for f in args.format.split(",") if f in SUB_FORMATS] or ["srt"]:
            fn, _ = SUB_FORMATS[fmt]
            for mode, suffix in (("ar", args.lang), ("bi", "bilingual")):
                p = out / f"{base}.{suffix}.{fmt}"
                p.write_text(("" if fmt == "vtt" else "﻿") + fn(data.cues, mode), encoding="utf-8")
                written.append(p)
        s.flush()
        await http.close()
        print(f"\n  Done in {time.time() - t0:.1f}s")
        for p in written:
            print(f"   {p}")

    asyncio.run(run())


def _pip(*args: str) -> bool:
    return subprocess.call([sys.executable, "-m", "pip", "--disable-pip-version-check", *args]) == 0


def setup(args: argparse.Namespace) -> None:
    config.ensure_dirs()
    voice_only = getattr(args, "voice_only", False)  # the installed app comes with its packages and web build
    if not voice_only:
        print("\n  Installing Python packages…")
        if not _pip("install", "-r", str(config.REQUIREMENTS)):
            raise SystemExit("  pip install failed")
    if not config.PIPER_MODEL.exists():
        print("  Downloading the offline Arabic voice (Piper, ~60 MB)…")
        try:
            from .desktop import download_voice

            asyncio.run(download_voice())  # one event loop for both files: the HTTP client belongs to its loop
        except Exception as e:  # noqa: BLE001
            print(f"  Piper voice download failed ({e}); dubbing will use the online voices only.")
    if voice_only:
        return
    npm = shutil.which("npm")
    if npm and not config.FRONTEND_DIST.joinpath("index.html").exists():
        print("  Building the web app…")
        frontend = config.PROJECT_ROOT / "frontend"
        if subprocess.call([npm, "install", "--no-audit", "--no-fund"], cwd=frontend) == 0:
            subprocess.call([npm, "run", "build"], cwd=frontend)
    elif not npm:
        print("  Node.js not found: install it from https://nodejs.org to build the web app.")
    print("\n  Ready. The Whisper model downloads itself the first time you use it.\n")


def update(_args: argparse.Namespace) -> None:
    ok = _pip("install", "-U", "yt-dlp", "edge-tts")
    if not ok and (config.PROJECT_ROOT / "installed.txt").exists():
        # The installed app lives in Program Files, which only an administrator can change.
        print("\n  Updating needs administrator rights: right-click Tarjuman.cmd in the install folder, "
              "choose Run as administrator, and run it with:  update")
    raise SystemExit(0 if ok else 1)


def doctor(_args: argparse.Namespace) -> None:
    def line(ok: bool, label: str, extra: str = "") -> None:
        print(f"  {'OK ' if ok else '-- '} {label}{'  ' + extra if extra else ''}")

    def mod(name: str) -> str | None:
        try:
            m = __import__(name)
            return str(getattr(m, "__version__", "") or getattr(getattr(m, "version", None), "__version__", "") or "ok")
        except Exception:  # noqa: BLE001
            return None

    print(f"\n  Tarjuman {__version__}\n")
    line(True, "Python", sys.version.split()[0])
    for name, label in (("fastapi", "FastAPI"), ("yt_dlp", "yt-dlp"), ("faster_whisper", "faster-whisper"),
                        ("edge_tts", "edge-tts"), ("piper", "piper-tts"), ("anthropic", "anthropic"),
                        ("onnxruntime", "onnxruntime")):
        v = mod(name)
        line(v is not None, label, v or "missing: python -m tarjuman setup")
    from .media.ffmpeg import available

    line(available(), "ffmpeg")
    line(config.PIPER_MODEL.exists(), "Offline Arabic voice (Piper)")
    line(config.FRONTEND_DIST.joinpath("index.html").exists(), "Web app build", str(config.FRONTEND_DIST))
    try:
        import httpx

        httpx.get("https://www.youtube.com/generate_204", timeout=8)
        line(True, "YouTube reachable")
    except Exception as e:  # noqa: BLE001
        line(False, "YouTube reachable", str(e))
    print()


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="  %(message)s")
    for noisy in ("httpx", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    ap = argparse.ArgumentParser(prog="tarjuman", description="Watch any video in Arabic.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd")

    p_serve = sub.add_parser("serve", help="start the app (default)")
    p_app = sub.add_parser("app", help="start the app in a window of its own instead of the browser")
    for p in (ap, p_serve, p_app):
        p.add_argument("--port", type=int, default=config.DEFAULT_PORT)
        p.add_argument("--host", default=config.DEFAULT_HOST, help="127.0.0.1 = this computer only")
        p.add_argument("--no-open", action="store_true", help="don't open the browser")

    p_subs = sub.add_parser("subs", help="write subtitle files for a video")
    p_subs.add_argument("link")
    p_subs.add_argument("--lang", default="ar")
    p_subs.add_argument("--format", default="srt", help="srt,vtt,txt")

    p_setup = sub.add_parser("setup", help="install everything")
    p_setup.add_argument("--voice-only", action="store_true", help="only download the offline Arabic voice")
    sub.add_parser("update", help="update yt-dlp and edge-tts")
    sub.add_parser("doctor", help="check every component")

    args = ap.parse_args(argv)
    {"subs": subs, "setup": setup, "update": update, "doctor": doctor, "app": desktop}.get(args.cmd or "serve", serve)(args)


if __name__ == "__main__":
    main()
