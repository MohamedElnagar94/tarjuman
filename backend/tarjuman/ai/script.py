"""The AI dub script writer (optional): instead of a literal machine translation, natural spoken
lines that fit the time of each sentence."""

from __future__ import annotations

import json
from pathlib import Path

from ..core.errors import AppError
from ..core.store import Debounced, read_json, write_json
from ..translate.service import map_limit
from ..voice.catalog import LANG_LABEL
from .client import AiClient
from .settings import AiSettings

STYLE_GUIDE = {
    "msa": (
        "Simple, natural Modern Standard Arabic, the way a good documentary narrator speaks: short clear "
        "sentences, everyday vocabulary, no stiff or bookish phrasing."
    ),
    "egyptian": (
        "Natural Egyptian colloquial Arabic (عامية مصرية), the way a polite Egyptian YouTuber explains things "
        "to viewers. Clear and respectful, not slangy."
    ),
}

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "text": {"type": "string"}},
                "required": ["id", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["lines"],
    "additionalProperties": False,
}
SCRIPT_SHAPE = '{"lines":[{"id":0,"text":"..."}]}'


def script_system_prompt(tl: str, style: str) -> str:
    lang = LANG_LABEL.get(tl, tl)
    voice = STYLE_GUIDE.get(style, STYLE_GUIDE["msa"]) if tl == "ar" else f"Natural, conversational spoken {lang}."
    return "\n".join(
        [
            f"You write the voice-over script for dubbing a video into {lang}. A text-to-speech voice reads each "
            "line while the original speaker is talking, so every line has to fit in the time the speaker took.",
            "",
            f"Style: {voice}",
            "",
            "For each input line:",
            "- Convey the meaning of `source` the way a native speaker would say it aloud. Do not translate word for word.",
            "- Stay within `max_chars` characters. This is a hard limit: a longer line cannot be spoken in time. "
            "Shorter is fine; drop filler and repetition before dropping meaning.",
            "- Keep product names, software and technical terms in their usual Latin spelling when that is how "
            "speakers of the language say them (for example Unreal Engine, Blueprint, ChatGPT).",
            "- Use commas and full stops where a speaker would pause; the voice uses them for natural rhythm.",
            "- Use the `context` lines (already dubbed) so the script flows naturally from line to line.",
            "",
            "Return exactly one output line per input `id`, in the same order. Never merge, split or skip lines.",
        ]
    )


class ScriptWriter:
    def __init__(self, settings: AiSettings, client: AiClient, cache_file: Path):
        self.settings = settings
        self.client = client
        self.cache_file = cache_file
        self.cache: dict[str, str] = {}
        self._save = Debounced(lambda: write_json(self.cache_file, self.cache), 2.0)

    def load(self) -> None:
        self.cache = {k: v for k, v in read_json(self.cache_file, {}).items() if isinstance(v, str)}

    def flush(self) -> None:
        self._save.flush()

    async def write(self, items: list[dict], *, tl: str = "ar", context: list[str] | None = None) -> dict[str, str]:
        """``items``: [{src, maxChars, seconds}] → {src: dub line}. Lines that fail are left out and the
        caller falls back to the plain translation."""
        a = self.settings.ai
        style = a["style"] if tl == "ar" else "-"

        def key_of(it: dict) -> str:
            return f"{a['provider']}|{self.settings.model}|{style}|{tl}|{-(-it['maxChars'] // 10)}|{it['src']}"

        out: dict[str, str] = {}
        todo = []
        for it in items:
            hit = self.cache.get(key_of(it))
            if hit:
                out[it["src"]] = hit
            else:
                todo.append(it)
        if not todo:
            return out

        system = script_system_prompt(tl, style)
        # A small first batch so live dubbing starts quickly.
        chunks, k = [], 0
        while k < len(todo):
            size = 6 if k == 0 else 25
            chunks.append(todo[k : k + size])
            k += size

        async def run(chunk: list[dict]) -> None:
            payload = {
                "context": (context or [])[-3:],
                "lines": [
                    {"id": i, "source": it["src"], "max_chars": it["maxChars"], "seconds": round(it["seconds"], 1)}
                    for i, it in enumerate(chunk)
                ],
            }
            try:
                res = await self.client.complete(
                    system, json.dumps(payload, ensure_ascii=False), schema=SCRIPT_SCHEMA, shape=SCRIPT_SHAPE
                )
            except AppError as e:
                self.settings.stats["lastError"] = e.message
                self.settings.stats["failed"] += len(chunk)
                if e.code in ("AI_AUTH", "AI_SDK_MISSING"):
                    raise
                return
            except Exception as e:  # noqa: BLE001 — bad JSON etc.: fall back to translation
                self.settings.stats["lastError"] = str(e)[:200]
                self.settings.stats["failed"] += len(chunk)
                return
            for line in (res or {}).get("lines") or []:
                idx = line.get("id")
                it = chunk[idx] if isinstance(idx, int) and 0 <= idx < len(chunk) else None
                text = " ".join(str(line.get("text") or "").split())
                if not it or not text:
                    continue
                out[it["src"]] = text
                self.cache[key_of(it)] = text
                self.settings.stats["lines"] += 1
            self._save.touch()

        await map_limit(chunks, 2, run)
        return out

    async def test(self) -> str:
        res = await self.client.complete(
            script_system_prompt("ar", self.settings.ai["style"]),
            json.dumps(
                {
                    "context": [],
                    "lines": [
                        {
                            "id": 0,
                            "source": "So in this tutorial I'm gonna show you how to basically build your first game, step by step.",
                            "max_chars": 70,
                            "seconds": 5,
                        }
                    ],
                }
            ),
            schema=SCRIPT_SCHEMA,
            shape=SCRIPT_SHAPE,
        )
        lines = (res or {}).get("lines") or []
        return str(lines[0].get("text") or "") if lines else ""
