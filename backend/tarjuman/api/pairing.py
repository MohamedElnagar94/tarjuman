"""Pairing: other devices on the Wi-Fi (a phone) must be paired before they can use the API.

The computer running the app is always allowed. Another device opens ``/pair?code=<invite>`` once
(the QR code shown on the computer). That gives this device its own key, stored in a long-lived
HttpOnly cookie, so every paired device is listed and can be removed on its own. The invite code
pairs any number of devices; a new invite code stops the old QR from pairing more, without unpairing
anyone. Only a hash of each device key is stored.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from pathlib import Path

from ..core.store import Debounced, read_json, write_json

COOKIE = "tarjuman_pair"
HEADER = "x-tarjuman-pair"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def device_name(ua: str) -> str:
    """A readable name from the browser's User-Agent: "Android · SM-S918B · Chrome", "iPhone · Safari"."""
    ua = str(ua or "")
    if "iPhone" in ua:
        system = "iPhone"
    elif "iPad" in ua:
        system = "iPad"
    elif m := re.search(r"Android [\d.]+; ([^;)]+?)(?: Build/[^;)]*)?[;)]", ua):
        model = m.group(1).strip()
        system = "Android" + (f" · {model}" if model and model.upper() != "K" else "")
    elif "Android" in ua:
        system = "Android"
    elif "Windows" in ua:
        system = "Windows"
    elif "Macintosh" in ua:
        system = "Mac"
    elif "Linux" in ua:
        system = "Linux"
    else:
        system = "?"
    for pat, name in (
        (r"EdgA?/|Edg/", "Edge"), (r"SamsungBrowser/", "Samsung Internet"), (r"OPR/|Opera", "Opera"),
        (r"Firefox/|FxiOS/", "Firefox"), (r"CriOS/|Chrome/", "Chrome"), (r"Safari/", "Safari"),
    ):
        if re.search(pat, ua):
            return f"{system} · {name}"
    return system


class Pairing:
    def __init__(self, file: Path):
        self.file = file
        self.code = ""
        self.devices: list[dict] = []
        self._legacy = ""  # the single shared secret of the first version, accepted once to migrate
        self._save_soon = Debounced(self._save, 30)

    def load(self) -> None:
        j = read_json(self.file, {})
        self.code = str(j.get("code") or j.get("secret") or "")
        self._legacy = str(j.get("secret") or "")
        self.devices = [d for d in j.get("devices") or [] if isinstance(d, dict) and d.get("hash")]
        if len(self.code) < 20:
            self.new_code()

    def _save(self) -> None:
        write_json(self.file, {"code": self.code, "devices": self.devices}, private=True)

    def flush(self) -> None:
        self._save_soon.flush()

    # ---------------- invite code ----------------

    def new_code(self) -> str:
        """A new invite: the old QR stops pairing new devices. Paired devices stay paired."""
        self.code = secrets.token_urlsafe(18)
        self._legacy = ""
        self._save()
        return self.code

    def valid_code(self, candidate: str | None) -> bool:
        return bool(candidate) and bool(self.code) and hmac.compare_digest(str(candidate), self.code)

    # ---------------- devices ----------------

    def pair(self, ua: str = "", ip: str = "") -> str:
        """Registers a device and returns its own key (to be kept in its cookie)."""
        token = secrets.token_urlsafe(24)
        now = int(time.time() * 1000)
        self.devices.append({
            "id": secrets.token_hex(4), "hash": _hash(token), "name": device_name(ua), "ua": str(ua)[:300],
            "pairedAt": now, "lastSeen": now, "lastIp": ip or "",
        })
        self._save()
        return token

    def device(self, token: str | None) -> dict | None:
        if not token:
            return None
        h = _hash(str(token))
        return next((d for d in self.devices if hmac.compare_digest(d["hash"], h)), None)

    def is_legacy(self, token: str | None) -> bool:
        return bool(token) and bool(self._legacy) and hmac.compare_digest(str(token), self._legacy)

    def seen(self, d: dict, ip: str) -> None:
        now = int(time.time() * 1000)
        if now - d.get("lastSeen", 0) > 60_000 or d.get("lastIp") != ip:
            d["lastSeen"], d["lastIp"] = now, ip
            self._save_soon.touch()

    def rename(self, device_id: str, name: str) -> bool:
        d = next((x for x in self.devices if x["id"] == device_id), None)
        if not d or not name.strip():
            return False
        d["name"] = name.strip()[:60]
        self._save()
        return True

    def remove(self, device_id: str) -> bool:
        n = len(self.devices)
        self.devices = [d for d in self.devices if d["id"] != device_id]
        if len(self.devices) != n:
            self._save()
            return True
        return False

    def remove_all(self) -> None:
        """Unpair every device and make a new invite, so the old QR can't pair them back."""
        self.devices = []
        self.new_code()

    def public(self) -> list[dict]:
        keys = ("id", "name", "pairedAt", "lastSeen", "lastIp")
        return [{k: d.get(k) for k in keys} for d in sorted(self.devices, key=lambda d: -d.get("lastSeen", 0))]
