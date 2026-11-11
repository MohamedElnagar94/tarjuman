"""Tarjuman as a desktop app: the server runs inside this process and the web app shows in a window
of its own instead of a browser tab. Closing the window stops the app.

The window is Edge (on every Windows 10 and 11) or Chrome in "app" mode: no address bar, no tabs, its
own taskbar button with Tarjuman's icon, and its own profile kept next to the data. Nothing extra is
installed for it. With neither browser, a normal browser tab opens instead.

Used by ``python -m tarjuman app`` (the installed Windows app starts this with pythonw, so there is
no console window; what would have been printed goes to ``data/tarjuman.log``).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

from . import __version__, config

log = logging.getLogger("tarjuman.desktop")


def log_to_file() -> None:
    """Without a console (pythonw) there is nowhere to print: keep a small log next to the data."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    config.ensure_dirs()
    path = config.DATA / "tarjuman.log"
    try:
        if path.exists() and path.stat().st_size > 2_000_000:
            path.replace(path.with_suffix(".old.log"))
        stream = open(path, "a", encoding="utf-8", buffering=1)
    except OSError:
        return
    sys.stdout = sys.stderr = stream
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=stream, force=True)


def running_instance(port: int) -> str | None:
    """The address of a Tarjuman already running on this computer, if there is one."""
    import httpx

    for p in range(port, port + config.PORT_TRIES):
        try:
            j = httpx.get(f"http://127.0.0.1:{p}/api/health", timeout=0.6).json()
            if j.get("app") == "tarjuman":
                return f"http://127.0.0.1:{p}"
        except Exception:  # noqa: BLE001
            continue
    return None


async def download_voice() -> None:
    """Both files of the offline Arabic voice. It uses a client of its own: the shared one belongs to
    the server's event loop, and this runs in another (a setup command, or a background thread)."""
    import httpx

    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": config.UA}, timeout=httpx.Timeout(30, read=300)) as c:
        for url, dest in (
            (config.PIPER_URL + ".onnx.json", config.PIPER_MODEL.with_suffix(".onnx.json")),
            (config.PIPER_URL + ".onnx", config.PIPER_MODEL),
        ):
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_name(dest.name + ".part")
            async with c.stream("GET", url) as res:
                res.raise_for_status()
                with open(part, "wb") as fh:
                    async for chunk in res.aiter_bytes(1 << 16):
                        fh.write(chunk)
            part.replace(dest)


def ensure_voice_in_background() -> None:
    """The offline Arabic voice (about 60 MB), fetched once without holding up the window."""
    if config.PIPER_MODEL.exists():
        return

    def work() -> None:
        try:
            asyncio.run(download_voice())
            log.info("offline voice downloaded")
        except Exception as e:  # noqa: BLE001
            log.warning("offline voice download failed (%r); online voices are used meanwhile", e)

    threading.Thread(target=work, name="voice-download", daemon=True).start()


def ensure_env_file() -> None:
    """A .env next to the user's data, made from the example, so the settings are easy to find."""
    target = config.HOME / ".env"
    example = config.PROJECT_ROOT / ".env.example"
    if config.HOME != config.PROJECT_ROOT and not target.exists() and example.exists():
        try:
            config.HOME.mkdir(parents=True, exist_ok=True)
            target.write_bytes(example.read_bytes())
        except OSError:
            pass


def find_browser() -> str | None:
    """A browser that can show one page as an app window: Edge first, then Chrome."""
    if sys.platform == "win32":
        roots = [os.environ.get(v) for v in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        for rel in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
            for root in roots:
                if root and os.path.isfile(os.path.join(root, rel)):
                    return os.path.join(root, rel)
        return None
    if sys.platform == "darwin":
        for app in ("Google Chrome", "Microsoft Edge", "Chromium"):
            exe = f"/Applications/{app}.app/Contents/MacOS/{app}"
            if os.path.isfile(exe):
                return exe
        return None
    return next((x for x in map(shutil.which, ("google-chrome", "microsoft-edge", "chromium", "chromium-browser")) if x), None)


def window_profile():
    return config.DATA / "window"


def window_is_open() -> bool:
    """Whether the app window still exists. The browser holds a lock on its profile folder for as long
    as it runs; the process we started can't be watched instead, because Edge hands over to another
    process and exits at once."""
    profile = window_profile()
    if sys.platform != "win32":
        return os.path.lexists(profile / "SingletonLock")
    try:
        os.close(os.open(profile / "lockfile", os.O_RDWR))
    except FileNotFoundError:
        return False
    except OSError:
        return True  # held by the browser
    return False


def wait_for_window(proc: subprocess.Popen) -> None:
    """Returns when the window that ``proc`` opened has been closed."""
    deadline = time.time() + 30
    while time.time() < deadline and not window_is_open() and proc.poll() is None:
        time.sleep(0.2)  # the window is still coming up
    while window_is_open() or (sys.platform != "win32" and proc.poll() is None):
        time.sleep(0.7)


def open_window(url: str) -> subprocess.Popen | None:
    """The app window, with its own profile folder: that keeps it apart from the user's everyday
    browser, and keeps the app's preferences between runs."""
    exe = find_browser()
    if not exe:
        return None
    profile = window_profile()
    profile.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.Popen([
            exe, f"--app={url}", f"--user-data-dir={profile}", "--window-size=1280,820", "--no-first-run",
            "--no-default-browser-check", "--disable-background-mode", "--disable-features=msEdgeStartupBoost,Translate",
            "--autoplay-policy=no-user-gesture-required",
        ])
    except OSError as e:
        log.info("could not open the app window (%s)", e)
        return None


def run(host: str, port: int, free_port) -> None:
    import uvicorn

    log_to_file()
    ensure_env_file()
    url = running_instance(port)
    server = None
    if url is None:
        from .api.app import create_app

        port = free_port(host, port)
        url = f"http://127.0.0.1:{port}"
        server = uvicorn.Server(uvicorn.Config(create_app(port=port), host=host, port=port, log_level="warning", log_config=None))
        threading.Thread(target=server.run, name="server", daemon=True).start()
        for _ in range(400):
            if server.started:
                break
            time.sleep(0.05)
        ensure_voice_in_background()
    log.info("Tarjuman %s at %s", __version__, url)

    window = open_window(url)
    try:
        if window is not None:
            wait_for_window(window)
        else:
            log.info("no Edge or Chrome for an app window; opening the default browser")
            webbrowser.open(url)
            while server is not None and not server.should_exit:
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if server is not None:
            server.should_exit = True
            time.sleep(0.8)  # lets the server save its caches
