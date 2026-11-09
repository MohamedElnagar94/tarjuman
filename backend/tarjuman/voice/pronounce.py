"""Pronunciation dictionary: how a word should be spoken (e.g. "UE5" → "أنريل إنجن فايف").
Applied to the voice only, never to the written translation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from ..core.store import read_json, write_json


class PronunciationDict:
    def __init__(self, file: Path):
        self.file = file
        self.items: list[dict[str, str]] = []
        self._rules: list[tuple[re.Pattern, str]] = []
        self.on_change: list[Callable[[], None]] = []

    def load(self) -> None:
        self.set(read_json(self.file, []), save=False)

    def set(self, items, save: bool = True) -> list[dict[str, str]]:
        clean = []
        for x in items if isinstance(items, list) else []:
            if not isinstance(x, dict):
                continue
            f, t = str(x.get("from") or "").strip(), str(x.get("to") or "").strip()
            if f and t:
                clean.append({"from": f, "to": t})
        self.items = clean[:500]
        rules = []
        # Longest first, so "Unreal Engine 5" applies before "Unreal".
        for item in sorted(self.items, key=lambda x: -len(x["from"])):
            f = item["from"]
            if re.fullmatch(r"[ -~]+", f):  # Latin letters / digits: whole words only
                pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(f) + r"(?![A-Za-z0-9])", re.I)
            else:
                pat = re.compile(re.escape(f))
            rules.append((pat, item["to"]))
        self._rules = rules
        if save:
            write_json(self.file, self.items, indent=1)
            for fn in self.on_change:
                fn()
        return self.items

    def apply(self, text: str) -> str:
        t = str(text or "")
        for pat, to in self._rules:
            t = pat.sub(lambda _m, to=to: to, t)
        return t
