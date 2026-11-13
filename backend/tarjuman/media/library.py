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

UPLOAD_EXT = re.compile(
    r"^(mp4|mkv|webm|mov|m4v|avi|3gp|mpg|mpeg|ts|wmv|flv"
    r"|mp3|m4a|m4b|aac|wav|ogg|oga|opus|flac|amr|wma|aiff|aif|caf|weba|mka)$"
)
AUDIO_EXT = {"mp3", "m4a", "m4b", "aac", "wav", "oga", "opus", "flac", "amr", "wma", "aiff", "aif", "caf", "weba", "mka"}
MIME = {
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska",
    ".mov": "video/quicktime", ".avi": "video/x-msvideo", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".wav": "audio/wav", ".ogg": "audio/ogg", ".flac": "audio/flac", ".opus": "audio/ogg", ".oga": "audio/ogg",
    ".aac": "audio/aac", ".m4b": "audio/mp4", ".amr": "audio/amr", ".wma": "audio/x-ms-wma", ".aiff": "audio/aiff",
    ".aif": "audio/aiff", ".caf": "audio/x-caf", ".weba": "audio/webm", ".mka": "audio/x-matroska",
    ".3gp": "video/3gpp", ".mpg": "video/mpeg", ".mpeg": "video/mpeg", ".ts": "video/mp2t", ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
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
    kind: str = ""  # "audio" or "video" (what the file holds, not only its extension)
    asr: str = ""  # the Whisper model that made the transcript
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
            "kind": self.kind or kind_by_ext(self.path), "duration": round(self.duration or 0, 2), "asr": self.asr,
            "lang": self.lang, "lines": len(self.segments or []),
        }

    def mime(self) -> str:
        return MIME.get(self.path.suffix.lower(), "application/octet-stream")


def kind_by_ext(path: Path) -> str:
    return "audio" if path.suffix.lower().lstrip(".") in AUDIO_EXT else "video"


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
                    lang=v.get("lang") or "", duration=float(v.get("duration") or 0), kind=v.get("kind") or "",
                    asr=v.get("asr") or "", root=self.folder,
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

    def describe(self, m: MediaItem) -> None:
        """What the file really holds: a .webm or .ogg can be a voice note or a video, and an MP3 with
        cover art has a picture that is not a video."""
        from .probe import probe, repair_stream_file

        info = probe(m.path)
        if not info.get("duration") and repair_stream_file(m.path):
            info = probe(m.path)  # a browser recording, now with its length and an index to seek by
        m.kind = info.get("kind") or kind_by_ext(m.path)
        if info.get("duration"):
            m.duration = info["duration"]
        try:
            m.size = m.path.stat().st_size
        except OSError:
            pass

    def peaks_file(self, m: MediaItem) -> Path:
        return self.folder / f"{m.id}.peaks.json"

    def discard(self, m: MediaItem) -> None:
        self.items.pop(m.id, None)
        for p in (m.path, self.peaks_file(m)):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass

    def delete(self, media_id: str) -> bool:
        m = self.items.get(media_id)
        if not m:
            return False
        self.discard(m)
        self.save()
        return True
