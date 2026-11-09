"""JSON files on disk: safe reads, atomic writes, and debounced saving."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable


def read_json(path: Path, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj: Any, *, private: bool = False, indent: int | None = None) -> None:
    """Write atomically (temp file + rename). ``private`` makes the file owner-only (it may hold an API key)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    data = json.dumps(obj, ensure_ascii=False, indent=indent)
    if private:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
    else:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(data)
    os.replace(tmp, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


class Debounced:
    """Calls ``fn`` once, ``delay`` seconds after the last ``touch()``. ``flush()`` runs it now if pending."""

    def __init__(self, fn: Callable[[], None], delay: float = 1.2):
        self.fn = fn
        self.delay = delay
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._dirty = False

    def touch(self) -> None:
        with self._lock:
            self._dirty = True
            if self._timer is None:
                self._timer = threading.Timer(self.delay, self._run)
                self._timer.daemon = True
                self._timer.start()

    def _run(self) -> None:
        with self._lock:
            self._timer = None
            if not self._dirty:
                return
            self._dirty = False
        try:
            self.fn()
        except OSError:
            pass

    def flush(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if not self._dirty:
                return
            self._dirty = False
        try:
            self.fn()
        except OSError:
            pass
