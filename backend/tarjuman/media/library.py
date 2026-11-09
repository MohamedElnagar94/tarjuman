"""Videos from your computer or from any site, addressed as ``media:<id>`` links everywhere."""

from __future__ import annotations

import os
import re
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..core.store import read_json, write_json
from ..core.text import safe_name

UPLOAD_EXT = re.compile(r"^(mp4|mkv|webm|mov|m4v|avi|mp3|m4a|wav|ogg|flac)$")
MIME = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".mov": "video/quicktime", ".avi": "video/x-msvideo", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".wav": "audio/wav", ".ogg": "audio/ogg", ".flac": "audio/flac",
}


@dataclass
class MediaItem:
    id: str
    title: str
    file: str  # file name inside the media folder
    source: str  # "upload" or the original URL
    created: int  # ms
    size: int = 0
    segments: list[dict] | None = None  # Whisper transcript, saved with the video
    lang: str = ""
    duration: float = 0.0
    root: Path = field(default=Path("."), repr=False, compare=False)

    @property
    def path(self) -> Path:
        return Path(self.file) if os.path.isabs(self.file) else self.root / self.file

    @property
    def link(self) -> str:
        return "media:" + self.id

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "link": self.link, "title": self.title, "source": self.source,
            "created": self.created, "size": self.size, "transcribed": bool(self.segments),
        }

    def mime(self) -> str:
        return MIME.get(self.path.suffix.lower(), "application/octet-stream")


class MediaLibrary:
    def __init__(self, folder: Path):
        self.folder = folder
        self.index = folder / "media.json"
        self.items: dict[str, MediaItem] = {}

    def load(self) -> None:
        self.items = {}
        for k, v in (read_json(self.index, {}) or {}).items():
            try:
                self.items[k] = MediaItem(
                    id=v["id"], title=v.get("title") or k, file=v["file"], source=v.get("source", ""),
                    created=int(v.get("created") or 0), size=int(v.get("size") or 0), segments=v.get("segments"),
                    lang=v.get("lang") or "", duration=float(v.get("duration") or 0), root=self.folder,
                )
            except (KeyError, TypeError, ValueError):
                continue

    def save(self) -> None:
        out = {}
        for k, m in self.items.items():
            d = asdict(m)
            d.pop("root", None)
            out[k] = d
        write_json(self.index, out)

    def get(self, media_id: str) -> MediaItem | None:
        return self.items.get(media_id)

    def list(self) -> list[dict]:
        alive = [m for m in self.items.values() if m.path.exists()]
        return [m.public() for m in sorted(alive, key=lambda m: -m.created)]

    def new_item(self, title: str, ext: str, source: str) -> MediaItem:
        mid = secrets.token_hex(6)
        m = MediaItem(
            id=mid, title=safe_name(title) or mid, file=f"{mid}.{ext}", source=source,
            created=int(time.time() * 1000), root=self.folder,
        )
        self.items[mid] = m
        return m

    def upload_target(self, name: str) -> MediaItem:
        name = str(name or "video")[:200]
        stem, ext = os.path.splitext(name)
        ext = ext[1:].lower()
        return self.new_item(stem or "video", ext if UPLOAD_EXT.match(ext) else "mp4", "upload")

    def discard(self, m: MediaItem) -> None:
        self.items.pop(m.id, None)
        try:
            m.path.unlink(missing_ok=True)
        except OSError:
            pass

    def delete(self, media_id: str) -> bool:
        m = self.items.get(media_id)
        if not m:
            return False
        self.discard(m)
        self.save()
        return True
