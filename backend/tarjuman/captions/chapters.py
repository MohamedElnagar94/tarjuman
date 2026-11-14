"""A YouTube video's chapters, read from its description the way YouTube itself does: a list of
timestamped lines that starts at 0:00, has at least three entries in order, each 10 seconds or longer."""

from __future__ import annotations

import re
from typing import Any

# 0:00, 01:05, 1:02:03; not part of a longer number or time (12:30:45:00, 2024:10).
TIME = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,3}):([0-5]\d)(?![\d:])")
# What sits between a timestamp and its title: dashes, colons, bullets, brackets.
EDGE = " \t-–—:|•·*()[]{}>،"
# At the end only separators: a title may end in its own bracket ("Setup [new]").
TAIL = " 	-–—:|•·*>،"
MIN_GAP = 10
MIN_COUNT = 3
MAX_TITLE = 100


def _seconds(m: re.Match[str]) -> int:
    h, mm, ss = m.group(1), m.group(2), m.group(3)
    return (int(h) if h else 0) * 3600 + int(mm) * 60 + int(ss)


def parse_chapters(description: str, length: float = 0) -> list[dict[str, Any]]:
    """[{start, title}] in order, or [] when the description has no chapter list."""
    stamped: list[tuple[int, str]] = []
    for raw in str(description or "").splitlines():
        line = raw.strip()
        m = TIME.search(line)
        # The timestamp opens the line ("0:00 Intro") or closes it ("Intro - 0:00").
        if not m or (m.start() > 6 and m.end() < len(line) - 1):
            continue
        # The brackets around a timestamp go with it: "⌨️ (1:45) Installing Python".
        before = re.sub(r"[(\[]\s*$", "", line[: m.start()])
        after = re.sub(r"^\s*[)\]]", "", line[m.end() :])
        title = re.sub(r"\s+", " ", before + " " + after).lstrip(EDGE).rstrip(TAIL)
        # A second timestamp on the line ("0:00 - 1:30 Intro") belongs to the range, not the title.
        title = TIME.sub("", title).lstrip(EDGE).rstrip(TAIL)
        # Emoji and bullets in front of the title.
        title = re.sub(r"^[^\w]+", "", title).lstrip(EDGE).rstrip(TAIL)
        if title:
            stamped.append((_seconds(m), title[:MAX_TITLE]))

    # The list starts at 0:00 and runs while the times go up; later timestamps in the description
    # ("thanks to X at 12:30") are not chapters.
    start = next((k for k, (sec, _) in enumerate(stamped) if sec == 0), None)
    if start is None:
        return []
    chapters: list[dict[str, Any]] = []
    for sec, title in stamped[start:]:
        if chapters and sec <= chapters[-1]["start"]:
            break
        if length and sec >= length:
            break
        chapters.append({"start": sec, "title": title})
    if len(chapters) < MIN_COUNT:
        return []
    if any(b["start"] - a["start"] < MIN_GAP for a, b in zip(chapters, chapters[1:])):
        return []
    return chapters
