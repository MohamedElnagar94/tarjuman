"""From caption lines to a dub script: whole sentences, spoken filler removed, and a pace for each
sentence that keeps the voice continuous and in sync with the speaker."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..captions.models import Cue


def jround(x: float) -> int:
    """Round half up, like JavaScript's Math.round (Python's round() is banker's rounding)."""
    return math.floor(x + 0.5)


SENT_END = re.compile(r"[.!?…؟。][\"'”’)\]]*$")

# Filler makes the translation longer without adding meaning. Removed from the dub text only.
FILLERS = [
    re.compile(r"\b(?:um+|uh+|erm|hmm+)\b[,.]?\s*", re.I),
    re.compile(r",?\s*\b(?:you know|i mean|kind of|sort of|basically|literally|actually)\b,?", re.I),
    re.compile(r"^(?:(?:so|now|okay|ok|well|alright|all right|and|right)\b[,.]?\s+)+", re.I),
    re.compile(r",?\s*\b(?:really|just|pretty much|simply|obviously)\b", re.I),
    # Fast talkers' openers and padding.
    re.compile(r"^(?:honestly|definitely|anyway|anyways|of course)\b,?\s*", re.I),
    re.compile(r"\b(?:go ahead and|kind of like|you know what I mean)\b\s*", re.I),
]
# Wordy phrasings translate into long sentences; shorten them before translating.
SHORTER = [
    (re.compile(r"\bin order to\b", re.I), "to"),
    (re.compile(r"\ba lot of\b", re.I), "many"),
    (re.compile(r"\ba little bit\b", re.I), "a bit"),
    (re.compile(r"\b(?:I am|I'm) going to\b", re.I), "I'll"),
    (re.compile(r"\b(?:we are|we're) going to\b", re.I), "we'll"),
    (re.compile(r"\byou are going to\b|\byou're going to\b", re.I), "you'll"),
    (re.compile(r"\byou guys\b", re.I), "you"),
    (re.compile(r"\bis going to be\b", re.I), "will be"),
]
_NOT_SPEECH = re.compile(
    r"\[[^\]]{0,40}\]|\([^)]{0,25}(?:music|applause|laughter|موسيقى|تصفيق|ضحك)[^)]{0,10}\)", re.I
)


def clean_spoken(text: str) -> str:
    """Caption markers that are not speech: ">>" (new speaker), [Music] / [موسيقى], ♪."""
    t = re.sub(r">>+|&gt;&gt;", " ", str(text or ""))
    t = _NOT_SPEECH.sub(" ", t)
    t = re.sub(r"[♪♫]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def condense_for_dub(text: str) -> str:
    t = str(text or "")
    for pat in FILLERS:
        t = pat.sub(" ", t)
    for pat, to in SHORTER:
        t = pat.sub(to, t)
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r",([.!?])", r"\1", t)
    t = re.sub(r"^[,\s]+", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    if not t:
        return str(text or "").strip()
    return t[0].upper() + t[1:]


@dataclass
class Block:
    """One spoken sentence. ``text`` is what the voice says, filled in lazily (translation / AI)."""

    i: int
    start: float
    end: float
    slot: float
    parts: list[str]
    src: str
    cueAr: str
    text: str | None = None


def group_dub_blocks(cues: Sequence[Cue], *, use_ar: bool = False) -> list[Block]:
    """Caption lines break mid-sentence; speaking each line alone sounds choppy and falls behind.
    Merge lines into sentences. When the dub comes from YouTube's own translation, sentence ends
    are read from the translated punctuation."""

    def text_of(src: str, ar: str) -> str:
        return (ar or src if use_ar else src or ar) or ""

    usable = [c for c in cues if (c.src or c.ar) and c.end > c.start]
    punctuated = sum(1 for c in usable if SENT_END.search(text_of(c.src, c.ar).strip()))
    has_punct = punctuated / max(1, len(usable)) > 0.15
    max_dur = 16 if has_punct else 8

    groups: list[dict] = []
    cur: dict | None = None
    for c in usable:
        if cur:
            gap = c.start - cur["end"]
            last = text_of(cur["src"][-1], cur["ar"][-1]).strip()
            sentence_done = bool(SENT_END.search(last)) if has_punct else False
            if gap > 0.9 or c.end - cur["start"] > max_dur or (sentence_done and cur["end"] - cur["start"] >= 1.2):
                groups.append(cur)
                cur = None
        if cur is None:
            cur = {"start": c.start, "end": c.end, "src": [], "ar": []}
        cur["end"] = max(cur["end"], c.end)
        cur["src"].append(c.src or "")
        cur["ar"].append(c.ar or "")
    if cur:
        groups.append(cur)

    out: list[Block] = []
    for i, g in enumerate(groups):
        nxt = groups[i + 1] if i + 1 < len(groups) else None
        slot = max(g["end"] - g["start"], nxt["start"] - g["start"] - 0.12) if nxt else g["end"] - g["start"] + 1.5
        srcs = [s for s in g["src"] if s]
        out.append(
            Block(
                i=i,
                start=round(g["start"], 3),
                end=round(g["end"], 3),
                slot=round(max(0.6, slot), 3),
                parts=srcs,
                src=condense_for_dub(clean_spoken(" ".join(srcs))),
                cueAr=clean_spoken(" ".join(a for a in g["ar"] if a)),
            )
        )
    return out


@dataclass(frozen=True)
class Pace:
    gap: float = 1.2  # a longer pause starts a new paragraph
    early: float = 0.5  # inside a paragraph a sentence may start this much early to keep the flow
    min_f: float = 0.92  # with spare time, slow down a little instead of going silent
    max_f: float = 1.5
    tail: float = 1.0  # the end of a paragraph may borrow from the pause after it
    breath: float = 0.12  # breath between sentences
    max_lag: float = 0.8  # the most the dub may trail the speaker


PACE = Pace()


def pace_blocks(
    blocks: Sequence[dict], dur: Callable[[dict], float], follow_start: float = math.inf, p: Pace = PACE
) -> list[dict]:
    """A real narrator doesn't race one sentence and crawl the next; they keep a continuous rhythm.

    For each sentence we look at a window of what's coming (~12 s, up to the end of the paragraph) and
    pick the speed that finishes that window on time, measured from where the dub actually is now:
     - a sentence with spare time covers a crowded one (no normal sentence followed by a rushed one)
     - if the dub fell behind, the next sentences speed up a little on their own until it catches up
     - the speed changes gradually between neighbours (no audible jumps)

    ``blocks`` are dicts with at least ``start`` and ``end``, sorted. ``dur(b)`` is the speech length
    at normal speed. Returns copies with ``at`` (when to start), ``slot`` (its time) and ``rate`` (%).
    """
    n = len(blocks)
    run_end = [0.0] * n
    for k in range(n - 1, -1, -1):
        nxt = blocks[k + 1] if k + 1 < n else None
        if not nxt or nxt["start"] - blocks[k]["end"] > p.gap:
            next_start = nxt["start"] if nxt else follow_start
            run_end[k] = blocks[k]["end"] + max(0.0, min(p.tail, next_start - blocks[k]["end"] - 0.3))
        else:
            run_end[k] = run_end[k + 1]

    res: list[dict] = []
    prev_end = -math.inf
    prev_f = 1.0
    for k in range(n):
        b = blocks[k]
        new_run = k == 0 or b["start"] - blocks[k - 1]["end"] > p.gap
        at = max(b["start"], prev_end + p.breath) if new_run else max(prev_end + p.breath, b["start"] - p.early)

        # The window: the coming sentences of this paragraph, up to ~12 s.
        speech = 0.0
        win_end = b["end"]
        for j in range(k, n):
            if j > k and blocks[j]["start"] - blocks[j - 1]["end"] > p.gap:
                break
            speech += dur(blocks[j]) + (p.breath if j > k else 0.0)
            next_in_run = j + 1 < n and blocks[j + 1]["start"] - blocks[j]["end"] <= p.gap
            win_end = blocks[j + 1]["start"] if next_in_run else run_end[j]
            if win_end - at >= 12:
                break
        f = speech / max(0.6, win_end - at)
        if not new_run:
            f = min(prev_f + 0.1, max(prev_f - 0.08, f))  # gradual
        # Sync beats smoothness: a sentence must not end more than max_lag after the next one is due.
        nxt = blocks[k + 1] if k + 1 < n else None
        due = nxt["start"] if nxt and nxt["start"] - b["end"] <= p.gap else run_end[k]
        f = max(f, dur(b) / max(0.6, due + p.max_lag - at))
        f = min(p.max_f, max(p.min_f, f))
        prev_f = f
        prev_end = at + dur(b) / f
        res.append({**b, "at": at, "rate": jround((f - 1) * 100)})

    out: list[dict] = []
    for k, r in enumerate(res):
        nxt = res[k + 1] if k + 1 < len(res) else None
        until = nxt["at"] if nxt and nxt["start"] - r["end"] <= p.gap else run_end[k]
        out.append({**r, "at": round(r["at"], 3), "slot": round(max(0.6, until - r["at"]), 3)})
    return out


def fit_rate(rate: float, duration: float, room: float) -> int:
    """The rate (%) that makes audio of ``duration`` (made at ``rate``) fit in ``room`` seconds."""
    need = (1 + rate / 100) * (duration / room)
    return min(80, max(int(rate), jround((need - 1) * 100) + 3))


@dataclass
class SpeakerSplit:
    primary: str  # "auto-m" | "auto-f"
    median_f0: int
    per_sentence: dict[int, str] | None = field(default=None)


def split_speakers(indices: Sequence[int], f0s: Sequence[float]) -> SpeakerSplit:
    """Pick a male or female voice from the speaker's pitch. If a second speaker is clear (≥10% of the
    sentences), each sentence gets its speaker's voice. Pitch is smoothed over 3 sentences so one bad
    measurement doesn't flip the voice; unclear sentences keep the previous voice."""
    known = [f for f in f0s if 60 < f < 400]
    female = sum(1 for f in known if f > 165)
    primary = "auto-f" if female > len(known) / 2 else "auto-m"
    median = round(sorted(known)[len(known) // 2]) if known else 0
    minority = min(female, len(known) - female)
    if len(known) < 6 or minority < len(known) * 0.1:
        return SpeakerSplit(primary, median)

    g = [(1 if f > 165 else 0) if 60 < f < 400 else -1 for f in f0s]
    per: dict[int, str] = {}
    prev = 0
    for k, x in enumerate(g):
        win = [y for y in (g[k - 1] if k > 0 else None, x, g[k + 1] if k + 1 < len(g) else None) if y in (0, 1)]
        cur = (1 if sum(1 for y in win if y == 1) * 2 > len(win) else 0) if win else prev
        if x == -1:
            cur = prev
        prev = cur
        per[indices[k]] = "auto-f" if cur else "auto-m"
    return SpeakerSplit(primary, median, per)
