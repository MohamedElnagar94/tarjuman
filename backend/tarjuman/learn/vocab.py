"""My words: English words saved with the sentence they came from, exportable to Anki."""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from ..core.store import read_json, write_json

LIMIT = 5000


def _s(v: Any, n: int) -> str:
    return str(v or "")[:n]


class Vocab:
    def __init__(self, file: Path):
        self.file = file
        self.items: list[dict[str, Any]] = []

    def load(self) -> None:
        j = read_json(self.file, [])
        self.items = j if isinstance(j, list) else []

    def save(self) -> None:
        write_json(self.file, self.items[:LIMIT])

    def add(self, b: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Returns (item, duplicate). The same word from the same sentence is not saved twice."""
        word = _s(b.get("word"), 80).strip()
        try:
            t = float(b.get("t") or 0)
        except (TypeError, ValueError):
            t = 0.0
        item = {
            "id": secrets.token_hex(6),
            "word": word,
            "tr": _s(b.get("tr"), 300),
            "sentence": _s(b.get("sentence"), 400),
            "sentenceTr": _s(b.get("sentenceTr"), 400),
            "videoId": _s(b.get("videoId"), 20),
            "title": _s(b.get("title"), 200),
            "t": t,
            "at": int(time.time() * 1000),
        }
        dup = next((x for x in self.items if x["word"].lower() == word.lower() and x["sentence"] == item["sentence"]), None)
        if dup:
            return dup, True
        self.items.insert(0, item)
        self.save()
        return item, False

    def delete(self, item_id: str) -> None:
        n = len(self.items)
        self.items = [x for x in self.items if x.get("id") != item_id]
        if len(self.items) != n:
            self.save()

    def anki_csv(self) -> str:
        """Front: the word and its sentence. Back: the meaning and the sentence's translation."""

        def cell(s: str) -> str:
            return '"' + str(s or "").replace('"', '""') + '"'

        rows = []
        for x in self.items:
            front = x["word"] + (f"<br><small>{x['sentence']}</small>" if x.get("sentence") else "")
            back = x.get("tr", "") + (f"<br><small>{x['sentenceTr']}</small>" if x.get("sentenceTr") else "")
            rows.append(cell(front) + "," + cell(back))
        return "\n".join(rows)
