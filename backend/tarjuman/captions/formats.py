"""Subtitle files: SRT, WebVTT and plain text, in target / bilingual / source modes."""

from __future__ import annotations

from typing import Callable, Iterable

from .models import Cue


def srt_time(sec: float) -> str:
    ms = max(0, round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cue_body(c: Cue, mode: str) -> str:
    if mode == "bi":
        return "\n".join(x for x in (c.src, c.ar) if x)
    if mode == "src":
        return c.src or c.ar or ""
    return c.ar or c.src or ""


def to_srt(cues: Iterable[Cue], mode: str = "ar") -> str:
    parts: list[str] = []
    for c in cues:
        body = cue_body(c, mode).strip()
        if not body:
            continue
        parts.append(f"{len(parts) + 1}\n{srt_time(c.start)} --> {srt_time(max(c.end, c.start + 0.5))}\n{body}\n")
    return "\n".join(parts)


def to_vtt(cues: Iterable[Cue], mode: str = "ar") -> str:
    parts = ["WEBVTT", ""]
    for c in cues:
        body = cue_body(c, mode).strip()
        if not body:
            continue
        start = srt_time(c.start).replace(",", ".")
        end = srt_time(max(c.end, c.start + 0.5)).replace(",", ".")
        parts.append(f"{start} --> {end}\n{body.replace('-->', '→')}\n")
    return "\n".join(parts)


def to_txt(cues: Iterable[Cue], mode: str = "ar") -> str:
    lines = [b for b in (cue_body(c, mode).strip() for c in cues) if b]
    return ("\n\n" if mode == "bi" else "\n").join(lines)


SUB_FORMATS: dict[str, tuple[Callable[[Iterable[Cue], str], str], str]] = {
    "srt": (to_srt, "application/x-subrip"),
    "vtt": (to_vtt, "text/vtt"),
    "txt": (to_txt, "text/plain"),
}
