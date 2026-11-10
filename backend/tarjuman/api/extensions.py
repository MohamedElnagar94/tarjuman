"""Which browser extensions may use the API.

Any extension can send requests to 127.0.0.1, so "comes from an extension" is not enough. The first
extension that connects (normally Tarjuman's own, right after it is installed) is trusted; any other
one is refused until the user allows it in Settings. An unpacked extension's id depends on the folder
it was loaded from, so a fixed list would not work.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core.store import read_json, write_json

_EXT = re.compile(r"^(?:chrome|moz|edge)-extension://([^/]+)")


def extension_id(origin: str | None) -> str | None:
    m = _EXT.match(str(origin or ""))
    return m.group(1) if m else None


class ExtensionTrust:
    def __init__(self, file: Path):
        self.file = file
        self.allowed: list[str] = []
        self.pending: list[str] = []

    def load(self) -> None:
        j = read_json(self.file, {})
        self.allowed = [str(x) for x in j.get("allowed") or []]
        self.pending = [str(x) for x in j.get("pending") or [] if x not in self.allowed]

    def _save(self) -> None:
        write_json(self.file, {"allowed": self.allowed, "pending": self.pending})

    def check(self, ext_id: str) -> bool:
        if ext_id in self.allowed:
            return True
        if not self.allowed:  # the first one is trusted
            self.allowed.append(ext_id)
            self._save()
            return True
        if ext_id not in self.pending:
            self.pending = (self.pending + [ext_id])[-10:]
            self._save()
        return False

    def allow(self, ext_id: str) -> None:
        if ext_id not in self.allowed:
            self.allowed.append(ext_id)
        self.pending = [x for x in self.pending if x != ext_id]
        self._save()

    def remove(self, ext_id: str) -> None:
        self.allowed = [x for x in self.allowed if x != ext_id]
        self.pending = [x for x in self.pending if x != ext_id]
        self._save()
