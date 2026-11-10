"""Arabic words written the same but said differently: "الجمل" is الجُمَل (sentences) or الجَمَل
(the camel). Without diacritics the voice guesses, usually the commonest reading. The dub knows the
English sentence each line came from, so the English decides, and the diacritics go into the text the
voice reads only; the written subtitles stay as they are.

Each rule: the undiacritized word, an English cue, and the word with diacritics. A rule applies when its
cue is in the English source. Add rules here; for a word that is always said one way, the user's
pronunciation dictionary is simpler.
"""

from __future__ import annotations

import re

RULES: list[tuple[str, str, str]] = [
    # word, English cue (regex), diacritized
    ("جمل", r"\bsentences?\b", "جُمَل"),
    ("جمل", r"\bcamels?\b", "جَمَل"),
    ("علم", r"\b(scien\w*|knowledge|learning)\b", "عِلْم"),
    ("علم", r"\bflags?\b", "عَلَم"),
    ("كتب", r"\bbooks?\b", "كُتُب"),
    ("كتب", r"\b(wrote|written)\b", "كَتَبَ"),
    ("قدم", r"\b(introduc\w*|present\w*|provid\w*|offer\w*)\b", "قَدَّمَ"),
    ("قدم", r"\b(foot|feet)\b", "قَدَم"),
    ("درس", r"\blessons?\b", "دَرْس"),
    ("درس", r"\bstudied\b", "دَرَسَ"),
    ("شعر", r"\bhair\b", "شَعْر"),
    ("شعر", r"\bpo(em|etry|et)s?\b", "شِعْر"),
    ("شعر", r"\bfelt\b", "شَعَرَ"),
    ("حب", r"\blove\b", "حُبّ"),
    ("حب", r"\b(seeds?|grains?|pills?)\b", "حَبّ"),
    ("عقد", r"\bcontracts?\b", "عَقْد"),
    ("عقد", r"\bdecades?\b", "عِقْد"),
    ("عقد", r"\bnodes?\b", "عُقَد"),
    ("دور", r"\broles?\b", "دَوْر"),
    ("دور", r"\b(floors?|stor(ey|ies))\b", "دَوْر"),
    ("نقد", r"\b(critic\w*)\b", "نَقْد"),
    ("نقد", r"\b(cash|money)\b", "نَقْد"),
]

# Prefixes that may stand before the word: و or ف, then ب ل or ك, then ال (or لل).
_PREFIX = r"([وف]?[بلك]?(?:ال|لل)?)"
_ARABIC_LETTER = r"ء-ي"


def _pattern(word: str) -> re.Pattern:
    return re.compile(rf"(?<![{_ARABIC_LETTER}]){_PREFIX}{word}(?![{_ARABIC_LETTER}ً-ْ])")


_COMPILED = [(_pattern(w), re.compile(cue, re.I), d) for w, cue, d in RULES]


def disambiguate(ar: str, src: str) -> str:
    """``ar`` with diacritics on the ambiguous words that the English ``src`` settles."""
    if not ar or not src:
        return ar
    for pat, cue, diacritized in _COMPILED:
        if cue.search(src):
            ar = pat.sub(lambda m, d=diacritized: m.group(1) + d, ar)
    return ar
