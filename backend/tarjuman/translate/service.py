"""Translate many lines with a disk cache. User corrections always win over machine translation."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Iterable

from ..captions.models import Cue
from ..core.store import Debounced, read_json, write_json
from ..core.text import norm_lang
from ..voice.gate import PriorityGate
from .providers import Google, GoogleExtension, MyMemory

BATCH_CHARS = 1400
BATCH_ITEMS = 24


def chunk_texts(texts: Iterable[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    cur: list[str] = []
    size = 0
    for t in texts:
        if cur and (size + len(t) + 1 > BATCH_CHARS or len(cur) >= BATCH_ITEMS):
            chunks.append(cur)
            cur, size = [], 0
        cur.append(t)
        size += len(t) + 1
    if cur:
        chunks.append(cur)
    return chunks


async def map_limit(items: list, limit: int, fn) -> list:
    """Run ``fn`` over items with at most ``limit`` in flight, keeping order."""
    out = [None] * len(items)
    it = iter(enumerate(items))

    async def worker() -> None:
        for i, x in it:
            out[i] = await fn(x)

    await asyncio.gather(*(worker() for _ in range(min(limit, len(items)))))
    return out


class Translator:
    def __init__(self, cache_file: Path, edits_file: Path):
        self.cache_file = cache_file
        self.edits_file = edits_file
        self.cache: dict[str, str] = {}
        self.edits: dict[str, str] = {}
        # Two Google endpoints with separate rate limits; when one refuses, the other usually still answers.
        self.googles = [GoogleExtension(), Google()]
        # Requests to the translators, most urgent first: the dub's next sentences (2–3) go ahead of
        # the background translation of a long video's subtitles (1).
        self.gate = PriorityGate(3)
        self.mymemory = MyMemory()
        self.stats = {"google": 0, "mymemory": 0, "failed": 0, "batches": 0, "lastProvider": ""}
        self._save = Debounced(self._write_cache, 1.2)
        self.edit_listeners: list[Callable[[str, str, str], None]] = []

    def load(self) -> None:
        self.cache = {k: v for k, v in read_json(self.cache_file, {}).items() if isinstance(v, str) and v}
        self.edits = {k: v for k, v in read_json(self.edits_file, {}).items() if isinstance(v, str) and v}

    def _write_cache(self) -> None:
        # Merge with what is on disk: another running copy of the app may have saved lines this one
        # doesn't have, and a plain overwrite would throw them away.
        merged = {k: v for k, v in read_json(self.cache_file, {}).items() if isinstance(v, str) and v}
        merged.update(dict(self.cache))
        write_json(self.cache_file, merged)

    def flush(self) -> None:
        self._save.flush()

    def has_edit(self, tl: str, src: str) -> bool:
        return f"{norm_lang(tl)}|{src}" in self.edits

    def lookup(self, tl: str, text: str) -> str | None:
        tl = norm_lang(tl)
        return self.edits.get(f"{tl}|{text}") or self.cache.get(f"{tl}|{text}")

    def set_edit(self, tl: str, src: str, ar: str) -> None:
        key = f"{norm_lang(tl)}|{src}"
        if ar:
            self.edits[key] = ar
        else:
            self.edits.pop(key, None)
        write_json(self.edits_file, self.edits, indent=1)
        for fn in self.edit_listeners:
            fn(norm_lang(tl), src, ar or self.cache.get(f"{norm_lang(tl)}|{src}", ""))

    @property
    def cooling(self) -> bool:
        """Every Google endpoint is pausing after rate limits."""
        return all(g.cooling for g in self.googles)

    async def translate_text(self, text: str, sl: str, tl: str) -> str:
        if not text.strip():
            return ""
        for g in self.googles:
            if g.cooling:
                continue
            try:
                out = await g.translate(text, sl, tl)
                self.stats["google"] += 1
                self.stats["lastProvider"] = g.name
                return out
            except Exception:  # noqa: BLE001 — next endpoint, then MyMemory
                pass
        try:
            out = await self.mymemory.translate(text, sl, tl)
            self.stats["mymemory"] += 1
            self.stats["lastProvider"] = "mymemory"
            return out
        except Exception:  # noqa: BLE001
            self.stats["failed"] += 1
        return ""

    async def translate_many(
        self,
        texts: Iterable[str],
        *,
        sl: str = "auto",
        tl: str = "ar",
        concurrency: int = 3,
        priority: int = 1,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, str]:
        """Returns {text: translation}. Texts that failed are left out so the caller can retry."""
        tl = norm_lang(tl) or "ar"
        unique = list(dict.fromkeys(t for t in texts if isinstance(t, str) and t.strip()))
        out: dict[str, str] = {}
        todo: list[str] = []
        for t in unique:
            hit = self.lookup(tl, t)
            if hit:
                out[t] = hit
            else:
                todo.append(t)
        done = len(out)
        if on_progress:
            on_progress(done, len(unique))

        def put(t: str, tr: str) -> None:
            if tr:
                out[t] = tr
                self.cache[f"{tl}|{t}"] = tr

        async def run(chunk: list[str]) -> None:
            nonlocal done
            res = None
            for g in self.googles:
                if g.cooling:
                    continue
                try:
                    res = await self.gate.run(priority, lambda g=g: g.translate_batch(chunk, sl, tl))
                except Exception:  # noqa: BLE001 — next endpoint
                    res = None
                if res:
                    self.stats["google"] += len(chunk)
                    self.stats["batches"] += 1
                    self.stats["lastProvider"] = g.name
                    break
            if res:
                for t, tr in zip(chunk, res):
                    put(t, tr)
            else:
                for t in chunk:
                    tr = await self.gate.run(priority, lambda t=t: self.translate_text(t, sl, tl))
                    put(t, tr)
                    if not tr and self.cooling:
                        break  # every provider is refusing: stop instead of hammering them line by line
            done += len(chunk)
            if on_progress:
                on_progress(done, len(unique))

        await map_limit(chunk_texts(todo), concurrency, run)
        if todo:
            self._save.touch()
        return out

    async def translate_cues(
        self, cues: list[Cue], *, sl: str = "en", tl: str = "ar", on_progress=None
    ) -> list[Cue]:
        found = await self.translate_many((c.src for c in cues), sl=sl, tl=tl, on_progress=on_progress)
        for c in cues:
            if c.src:
                c.ar = found.get(c.src) or c.ar or ""
        return cues
