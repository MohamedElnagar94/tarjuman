from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Line:
    """A raw caption line from a track."""

    start: float
    end: float
    text: str


@dataclass
class Cue:
    """A caption line with its source text and its translation (``ar`` holds any target language)."""

    start: float
    end: float
    src: str
    ar: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VideoCues:
    videoId: str
    title: str
    author: str
    lengthSeconds: int
    tl: str
    alreadyTranslated: bool
    asr: bool
    srcLang: str
    cues: list[Cue] = field(default_factory=list)
    autoTranslated: bool = False
    whisper: bool = False
    media: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cues"] = [c.to_dict() for c in self.cues]
        return d
