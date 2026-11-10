"""Turn raw caption tracks into clean lines: rolling repeats, roll-up captions, ASR sentences, alignment."""

from __future__ import annotations

import re
from dataclasses import replace

from .models import Line

_SENT_BOUND = re.compile(r"[.!?…](?=\s|$)")


def dedupe_rolling(lines: list[Line]) -> list[Line]:
    """Some ASR tracks repeat a growing window ("so we" → "so we went home"); keep the longest."""
    out: list[Line] = []
    for c in lines:
        prev = out[-1] if out else None
        if prev and len(c.text) > len(prev.text) and c.text.startswith(prev.text):
            prev.text = c.text
            prev.end = max(prev.end, c.end)
            prev.words = c.words
            continue
        out.append(replace(c))
    return out


def normalize_lines(raw: list[Line]) -> list[Line]:
    """Give lines with no duration an end: up to the next line, at most 6 s (3 s for the last one)."""
    lines = [c for c in raw if c and c.text]
    for i, c in enumerate(lines):
        if not c.end > c.start:
            nx = lines[i + 1] if i + 1 < len(lines) else None
            c.end = min(nx.start, c.start + 6) if nx and nx.start > c.start else c.start + 3
    return lines


def unroll_lines(lines: list[Line]) -> list[Line]:
    """Roll-up captions (many channels, e.g. freeCodeCamp): each line stays on screen while the next
    appears below it, and the new line often repeats the end of the previous one. Taken as they are,
    the text repeats and the dub speaks choppy fragments. Keep only the new words of each line, and end
    each line where the next one starts."""
    if len(lines) < 4:
        return lines
    overlapping = sum(1 for i in range(1, len(lines)) if lines[i].start < lines[i - 1].end - 0.3)
    if overlapping < len(lines) * 0.3:
        return lines

    def norm(w: str) -> str:
        return re.sub(r"[^\w']", "", w.lower())

    out: list[Line] = []
    prev_words: list[str] = []
    for c in lines:
        words = c.text.split()
        # The longest repeat: the last k words of the previous line equal the first k of this one.
        k = min(len(prev_words), len(words))
        while k > 0:
            if all(norm(prev_words[len(prev_words) - k + j]) == norm(words[j]) for j in range(k)):
                break
            k -= 1
        prev_words = words
        fresh = words[k:]
        if fresh:
            timed = c.words[k:] if c.words and len(c.words) == len(words) else None
            out.append(Line(timed[0][0] if timed else c.start, c.end, " ".join(fresh), timed))
    for i in range(len(out) - 1):
        out[i].end = max(out[i].start + 0.3, min(out[i].end, out[i + 1].start))
    return out


PAUSE = 0.45  # silence (beyond the time a word takes to say) that ends a sentence
MIN_SENTENCE = 2.0
MAX_SENTENCE = 7.0
FILLERS = {"uh", "um", "uhm", "erm", "hmm", "ah"}


def split_at_pauses(group: list[Line]) -> list[Line] | None:
    """Auto captions often have no punctuation at all, so a whole talk would come out as one endless
    "sentence" cut every ~17 s: slow to dub and read as one breathless block. Their words are timed,
    though, so cut where the speaker actually pauses: 2–7 s sentences that follow the speech."""
    words: list[tuple[float, str]] = []
    for line in group:
        if not line.words:
            return None
        words.extend(line.words)
    if len(words) < 4:
        return None

    def pause_before(k: int) -> float:
        t, w = words[k - 1]
        score = words[k][0] - t - 0.06 * len(w) - 0.1
        if words[k][1].lower().strip(",.") in FILLERS:
            score += 0.4  # "uh" usually starts a new thought
        return score

    cuts = [0]
    k = 1
    while k < len(words):
        start = words[cuts[-1]][0]
        dur = words[k][0] - start
        if dur >= MIN_SENTENCE and pause_before(k) >= PAUSE:
            # A lone word between two pauses ("…large language ‖ models ‖ large language models represent")
            # usually finishes the phrase before it, so it stays with that sentence.
            lone = k + 1 < len(words) and pause_before(k + 1) >= PAUSE and words[k + 1][0] - words[k][0] < 1.5
            if lone and words[k][1].lower().strip(",.") not in FILLERS:
                k += 1
            cuts.append(k)
        elif dur >= MAX_SENTENCE:
            # Too long without a clear pause: cut at the longest pause in its second half.
            options = [j for j in range(cuts[-1] + 1, k + 1) if words[j][0] - start >= MAX_SENTENCE / 2]
            cuts.append(max(options or [k], key=pause_before))
            k = cuts[-1]
        k += 1

    out: list[Line] = []
    bounds = cuts + [len(words)]
    for a, b in zip(bounds, bounds[1:]):
        text = " ".join(w for _, w in words[a:b]).strip()
        if not text:
            continue
        end = words[b][0] if b < len(words) else group[-1].end
        out.append(Line(words[a][0], max(end, words[a][0] + 0.6), text))
    return out


def reconstruct_asr(raw: list[Line]) -> list[Line]:
    """ASR captions arrive chopped mid-sentence. Join them back into sentences so they translate well."""
    atoms = dedupe_rolling([c for c in raw if c.text])
    if not atoms:
        return []

    groups: list[list[Line]] = []
    cur: list[Line] = []
    for a in atoms:
        if cur and a.start - cur[-1].end > 1.8:
            groups.append(cur)
            cur = []
        cur.append(a)
    if cur:
        groups.append(cur)

    segs: list[Line] = []
    for g in groups:
        text = ""
        marks: list[tuple[int, int]] = []  # (char offset, atom index)
        for i, a in enumerate(g):
            if text:
                text += " "
            marks.append((len(text), i))
            text += a.text
        bounds = [0] + [m.end() for m in _SENT_BOUND.finditer(text) if m.end() >= 8] + [len(text)]
        if len(bounds) == 2 and len(text) > 120:
            paused = split_at_pauses(g)
            if paused:
                segs.extend(paused)
                continue
        for b in range(len(bounds) - 1):
            s, e = bounds[b], bounds[b + 1]
            if e <= s:
                continue
            seg_text = text[s:e].strip()
            if not seg_text:
                continue
            idxs = [i for ch, i in marks if s <= ch < e]
            if not idxs:
                continue
            first, last = g[min(idxs)], g[max(idxs)]
            segs.append(Line(first.start, max(last.end, first.start + 0.8), seg_text))

    # Re-cut over-long lines proportionally, preferring a comma.
    res: list[Line] = []
    for s in segs:
        if len(s.text) <= 240:
            res.append(s)
            continue
        parts: list[str] = []
        buf = ""
        for w in s.text.split(" "):
            if buf and (len(buf) + 1 + len(w) > 220 or (len(buf) > 120 and re.search(r"[,;:]$", buf))):
                parts.append(buf)
                buf = w
            else:
                buf = f"{buf} {w}" if buf else w
        if buf:
            parts.append(buf)
        total = sum(len(p) + 1 for p in parts)
        dur = max(s.end - s.start, 0.8)
        acc = 0
        for p in parts:
            st = s.start + dur * acc / total
            acc += len(p) + 1
            en = min(s.start + dur * acc / total, s.end)
            res.append(Line(st, max(en, st + 0.6), p))

    for i in range(len(res) - 1):
        if res[i].end > res[i + 1].start:
            res[i].end = max(res[i].start + 0.4, res[i + 1].start)
    return res


def align_source(targets: list[Line], sources: list[Line]) -> list[str]:
    """Attach source-language lines to translated lines. The two tracks split speech in different
    places; attaching every overlapping source line would show a middle line under two targets and
    look repeated. Each source line goes to exactly one target: the one it overlaps most."""
    if not targets:
        return []
    parts: list[list[str]] = [[] for _ in targets]
    j = 0
    for s in sources:
        while j < len(targets) - 1 and targets[j].end <= s.start:
            j += 1
        best, best_ov = -1, 0.0
        k = max(0, j - 1)
        while k < len(targets) and targets[k].start < s.end:
            ov = min(s.end, targets[k].end) - max(s.start, targets[k].start)
            if ov > best_ov:
                best_ov, best = ov, k
            k += 1
        if best < 0:
            # No overlap: the nearest line, if it is close.
            k = min(j, len(targets) - 1)
            if abs(targets[k].start - s.start) < 2:
                best = k
        if best >= 0:
            parts[best].append(s.text)
    return [re.sub(r"\s+", " ", " ".join(p)).strip() for p in parts]
