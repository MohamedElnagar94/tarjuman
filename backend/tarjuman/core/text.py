"""Small text helpers shared across modules."""

from __future__ import annotations

import html
import re

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_VIDEO_IN_URL = re.compile(r"(?:[?&]v=|/shorts/|/embed/|/live/|/v/|youtu\.be/)([A-Za-z0-9_-]{11})")
_MEDIA_LINK = re.compile(r"^media:[a-f0-9]{12}$")


def parse_video_id(link: str | None) -> str | None:
    if not link:
        return None
    s = str(link).strip()
    if _VIDEO_ID.match(s):
        return s
    m = _VIDEO_IN_URL.search(s)
    return m.group(1) if m else None


def is_media_link(link: str | None) -> bool:
    return bool(_MEDIA_LINK.match(str(link or "").strip()))


def media_id_of(link: str) -> str:
    return str(link).strip()[6:]


def video_key(link: str) -> str | None:
    """The id a job or cache uses for a link: the YouTube id, or the ``media:<id>`` link itself."""
    return str(link).strip() if is_media_link(link) else parse_video_id(link)


def work_id(video_id: str) -> str:
    """A folder-safe id (``media:`` links contain a colon, which Windows forbids in names)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(video_id))


def norm_lang(lang: str | None) -> str:
    return str(lang or "").lower().replace("_", "-").split("-")[0]


def decode_entities(s: str) -> str:
    return html.unescape(str(s))


def collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def safe_name(s: str | None) -> str:
    out = re.sub(r'[\\/:*?"<>|\r\n]+', " ", str(s or "video"))
    out = re.sub(r"\s+", " ", out).strip()[:80]
    return out or "video"


def mmss(sec: float) -> str:
    sec = max(0, int(sec))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def chars_of(text: str) -> int:
    return len(collapse_ws(text))
