"""Parse YouTube caption bodies: timedtext XML (format 3) and json3."""

from __future__ import annotations

import json
import re

from ..core.text import collapse_ws, decode_entities
from .models import Line

_P = re.compile(r"<p\b([^>]*)>([\s\S]*?)</p>")
_TAG = re.compile(r"<[^>]*>")
_WORD = re.compile(r"<s\b([^>]*)>([\s\S]*?)</s>")


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(r"\b" + name + r'="([^"]*)"', attrs)
    return m.group(1) if m else None


def _to_ms(raw: str) -> int:
    try:
        v = float(raw)
    except ValueError:
        return 0
    return round(v * 1000) if "." in raw else round(v)


def parse_timed_text(xml: str) -> list[Line]:
    out: list[Line] = []
    for m in _P.finditer(xml):
        attrs = m.group(1)
        t_raw = _attr(attrs, "t")
        if t_raw is None:
            continue
        t = _to_ms(t_raw)
        d = _to_ms(_attr(attrs, "d") or "0")
        body = m.group(2)
        text = collapse_ws(decode_entities(_TAG.sub("", body)))
        if not text:
            continue
        words = []
        for s in _WORD.finditer(body):
            w = collapse_ws(decode_entities(_TAG.sub("", s.group(2))))
            if w:
                words.append(((t + _to_ms(_attr(s.group(1), "t") or "0")) / 1000, w))
        out.append(Line(t / 1000, (t + max(d, 0)) / 1000, text, words or None))
    return out


def parse_json3(data: dict) -> list[Line]:
    out: list[Line] = []
    for ev in data.get("events") or []:
        segs = ev.get("segs")
        if not segs:
            continue
        text = collapse_ws("".join(s.get("utf8") or "" for s in segs))
        if not text:
            continue
        start = (ev.get("tStartMs") or 0) / 1000
        words = [
            (start + (s.get("tOffsetMs") or 0) / 1000, collapse_ws(s.get("utf8") or ""))
            for s in segs
            if collapse_ws(s.get("utf8") or "")
        ]
        timed = len(words) > 1 and any(s.get("tOffsetMs") for s in segs)
        out.append(Line(start, start + (ev.get("dDurationMs") or 0) / 1000, text, words if timed else None))
    return out


def parse_captions(body: str | None) -> list[Line]:
    t = str(body or "").strip()
    if not t:
        return []
    if t.startswith("{"):
        try:
            return parse_json3(json.loads(t))
        except ValueError:
            return []
    return parse_timed_text(t)
