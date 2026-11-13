"""Updates for the installed Windows app, from the project's GitHub releases.

``check`` reads the releases newer than this version, with their notes (what was added and fixed), at
most every few hours unless asked. ``start_install`` downloads the installer, verifies it against the
SHA-256 file published next to it, starts it, and asks the desktop app to quit so its files can be
replaced. The installer then starts Tarjuman again. Nothing is installed without a matching checksum.

Only the installed app updates itself; a copy run from source shows the new version and its page.
Contacting GitHub is listed in Settings -> Privacy, and checking can be turned off (Settings -> Updates).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
import threading
import time
from typing import Any

from . import __version__, config

log = logging.getLogger("tarjuman.updates")

REPO = "MohamedElnagar94/tarjuman"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=20"
CHECK_EVERY = 6 * 3600  # seconds between automatic checks
INSTALLER = re.compile(r"^Tarjuman-Setup-[\d.]+\.exe$")
READY_DELAY = 1.5  # seconds the installer gets to start before the app closes


def parse_version(text: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(text or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def installed() -> bool:
    """The installed Windows app (not a copy run from source)."""
    return (config.PROJECT_ROOT / "installed.txt").exists()


def newer_releases(releases: list[dict], current: str) -> list[dict]:
    """Published releases newer than ``current``, newest first, each with what the update needs."""
    now = parse_version(current) or (0, 0, 0)
    out = []
    for r in releases:
        v = parse_version(r.get("tag_name", ""))
        if not v or v <= now or r.get("draft") or r.get("prerelease"):
            continue
        assets = {a.get("name", ""): a for a in r.get("assets") or []}
        exe = next((a for n, a in assets.items() if INSTALLER.match(n)), None)
        sha = assets.get(exe["name"] + ".sha256") if exe else None
        out.append({
            "version": ".".join(map(str, v)),
            "notes": str(r.get("body") or "").strip(),
            "date": r.get("published_at") or "",
            "page": r.get("html_url") or f"https://github.com/{REPO}/releases",
            "installer": {"name": exe["name"], "url": exe["browser_download_url"], "size": exe.get("size", 0)} if exe else None,
            "sha256": sha["browser_download_url"] if sha else None,
        })
    out.sort(key=lambda x: parse_version(x["version"]), reverse=True)
    return out


class Updater:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.checked_at = 0.0
        self.releases: list[dict] = []
        self.error = ""
        self.phase = "idle"  # idle | downloading | verifying | starting | error
        self.progress = 0
        self.message = ""

    # ---------------- check ----------------

    def check(self, force: bool = False) -> None:
        if not force and time.time() - self.checked_at < CHECK_EVERY:
            return
        import httpx

        try:
            r = httpx.get(API, headers={"Accept": "application/vnd.github+json", "User-Agent": "Tarjuman"}, timeout=15)
            r.raise_for_status()
            self.releases = newer_releases(r.json(), __version__)
            self.error = ""
        except Exception as e:  # noqa: BLE001
            log.info("update check failed: %s", e)
            self.error = "NETWORK"
        self.checked_at = time.time()

    def state(self) -> dict[str, Any]:
        latest = self.releases[0] if self.releases else None
        return {
            "current": __version__,
            "latest": latest["version"] if latest else None,
            "available": latest is not None,
            # The notes of every version between this one and the latest, newest first.
            "releases": [{k: r[k] for k in ("version", "notes", "date", "page")} for r in self.releases],
            "canInstall": bool(installed() and os.name == "nt" and latest and latest["installer"] and latest["sha256"]),
            "installed": installed(),
            "checkedAt": int(self.checked_at * 1000),
            "error": self.error,
            "phase": self.phase,
            "progress": self.progress,
            "message": self.message,
        }

    # ---------------- install ----------------

    def start_install(self, on_ready) -> bool:
        """Downloads, verifies and starts the latest installer in the background; ``on_ready`` is called
        once the installer is running (the desktop app then quits). False if it can't start."""
        st = self.state()
        if not st["canInstall"] or self.phase in ("downloading", "verifying", "starting"):
            return False
        threading.Thread(target=self._install, args=(self.releases[0], on_ready), daemon=True).start()
        return True

    def _install(self, release: dict, on_ready) -> None:
        import httpx

        folder = config.TMP / "update"
        folder.mkdir(parents=True, exist_ok=True)
        exe = folder / release["installer"]["name"]
        part = exe.with_name(exe.name + ".part")
        try:
            self.phase, self.progress, self.message = "downloading", 0, ""
            with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(30, read=120), headers={"User-Agent": "Tarjuman"}) as c:
                expected = c.get(release["sha256"]).text.split()[0].strip().lower()
                if not re.fullmatch(r"[0-9a-f]{64}", expected):
                    raise RuntimeError("the checksum file is not valid")
                digest = hashlib.sha256()
                with c.stream("GET", release["installer"]["url"]) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("content-length") or release["installer"]["size"] or 0)
                    done = 0
                    with open(part, "wb") as fh:
                        for chunk in r.iter_bytes(1 << 16):
                            fh.write(chunk)
                            digest.update(chunk)
                            done += len(chunk)
                            if total:
                                self.progress = min(99, done * 100 // total)
            self.phase = "verifying"
            if digest.hexdigest() != expected:
                part.unlink(missing_ok=True)
                raise RuntimeError("the download does not match its checksum")
            part.replace(exe)
            self.phase, self.progress = "starting", 100
            # The installer asks Windows for permission, replaces the program, and starts Tarjuman again.
            subprocess.Popen(
                [str(exe), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"],
                creationflags=0x00000008 | 0x00000200,  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                close_fds=True,
            )
            log.info("update %s started", release["version"])
            time.sleep(READY_DELAY)
            on_ready()
        except Exception as e:  # noqa: BLE001
            log.warning("update failed: %s", e)
            part.unlink(missing_ok=True)
            self.phase, self.message = "error", str(e)[:200]
