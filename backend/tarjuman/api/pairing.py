"""Pairing: other devices on the Wi-Fi (a phone) must be paired before they can use the API.

The computer running the app is always allowed. Any other device needs the pairing secret, which it
gets once by opening ``/pair?code=<secret>`` (a link or QR code shown on the computer). That sets a
long-lived cookie, so the phone's browser sends it with every request, video and audio file included.
Resetting the secret unpairs every device at once.
"""

from __future__ import annotations

import hmac
import secrets
from pathlib import Path

from ..core.store import read_json, write_json

COOKIE = "tarjuman_pair"
HEADER = "x-tarjuman-pair"


class Pairing:
    def __init__(self, file: Path):
        self.file = file
        self.secret = ""

    def load(self) -> None:
        self.secret = str(read_json(self.file, {}).get("secret") or "")
        if len(self.secret) < 20:
            self.reset()

    def reset(self) -> str:
        self.secret = secrets.token_urlsafe(18)
        write_json(self.file, {"secret": self.secret}, private=True)
        return self.secret

    def valid(self, candidate: str | None) -> bool:
        return bool(candidate) and bool(self.secret) and hmac.compare_digest(str(candidate), self.secret)
