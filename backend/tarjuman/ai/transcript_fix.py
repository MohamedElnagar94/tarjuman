"""After Whisper: the AI reads the whole transcript and fixes words that were clearly misheard (a name
written as a word that sounds alike, a word split in two), from the context. It keeps the dialect and
every line where it is; it never rewrites, summarises or translates. Optional (Settings ->
Transcription), and only with an AI set up in Settings -> AI: the text is sent to that provider."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("tarjuman.ai")

BATCH = 80

SCHEMA = {
    "type": "object",
    "properties": {"lines": {"type": "array", "items": {"type": "string"}}},
    "required": ["lines"],
    "additionalProperties": False,
}
SHAPE = '{"lines":["...","..."]}'


def system_prompt(lang: str, vocab: str) -> str:
    known = f"\nNames and words the speaker uses (write them exactly like this): {vocab}" if vocab else ""
    arabic = (
        "\nThe speech is Arabic, possibly a dialect (Egyptian, Gulf, Levantine, Maghrebi). Keep the dialect exactly: "
        "never turn it into Modern Standard Arabic, never 'correct' dialect words or grammar. Write a word the way it "
        "is normally spelled in that dialect (عايز، إزاي، مش)."
        if (lang or "").startswith("ar")
        else ""
    )
    return (
        "You fix speech-recognition errors in a transcript. Each input line is one numbered subtitle line.\n"
        "Change a word only when it is clearly a mishearing given the context: a name written as a word that sounds "
        "alike, a word split or merged wrongly, a nonsense word that sounds like a real one. Leave everything else "
        "exactly as it is, including filler words, repetitions and informal speech. Do not add, remove, reorder, "
        "summarise or translate anything. When unsure, keep the original.\n"
        "Return exactly one output line per input line, in the same order, without the numbers."
        + arabic
        + known
    )


async def fix_lines(client: Any, lines: list[str], lang: str = "", vocab: str = "") -> list[str]:
    """The corrected lines, same count and order. A batch the AI gets wrong (another count) keeps the
    original lines, so a correction can never shift or drop subtitles."""
    out: list[str] = []
    system = system_prompt(lang, vocab)
    for i in range(0, len(lines), BATCH):
        part = lines[i : i + BATCH]
        numbered = "\n".join(f"{n + 1}. {t}" for n, t in enumerate(part))
        try:
            res = await client.complete(system, numbered, schema=SCHEMA, shape=SHAPE, effort="low")
            got = [str(x).strip() for x in (res.get("lines") or [])]
        except Exception as e:  # noqa: BLE001 — the transcript stays as Whisper wrote it
            log.warning("transcript correction failed: %r", e)
            got = []
        if len(got) != len(part) or any(not g for g in got):
            out.extend(part)
        else:
            out.extend(_strip_number(g) for g in got)
    return out


def _strip_number(s: str) -> str:
    import re

    return re.sub(r"^\s*\d+[.)\-:]\s*", "", s)
