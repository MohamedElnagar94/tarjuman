"""The voices: Microsoft neural voices (free, online) and Piper (offline, Arabic).

Arabic and the first five languages are listed here by hand; every other language Microsoft speaks comes
from edge_voices.json (a man and a woman from its main region, generated from edge-tts's voice list)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..core.langs import NAMES, target

# The first voice of each language is its default.
VOICES: dict[str, list[dict[str, str]]] = {
    "ar": [
        {"id": "ar-EG-ShakirNeural", "name": "شاكر", "accent": "مصري", "gender": "m"},
        {"id": "ar-EG-SalmaNeural", "name": "سلمى", "accent": "مصري", "gender": "f"},
        {"id": "ar-SA-HamedNeural", "name": "حامد", "accent": "سعودي", "gender": "m"},
        {"id": "ar-SA-ZariyahNeural", "name": "زارية", "accent": "سعودي", "gender": "f"},
        {"id": "ar-AE-HamdanNeural", "name": "حمدان", "accent": "إماراتي", "gender": "m"},
        {"id": "ar-AE-FatimaNeural", "name": "فاطمة", "accent": "إماراتي", "gender": "f"},
        {"id": "ar-SY-LaithNeural", "name": "ليث", "accent": "سوري", "gender": "m"},
        {"id": "ar-SY-AmanyNeural", "name": "أماني", "accent": "سورية", "gender": "f"},
        {"id": "ar-JO-TaimNeural", "name": "تيم", "accent": "أردني", "gender": "m"},
        {"id": "ar-LB-LaylaNeural", "name": "ليلى", "accent": "لبنانية", "gender": "f"},
        {"id": "ar-MA-JamalNeural", "name": "جمال", "accent": "مغربي", "gender": "m"},
        {"id": "ar-IQ-RanaNeural", "name": "رنا", "accent": "عراقية", "gender": "f"},
    ],
    "en": [
        {"id": "en-US-AndrewNeural", "name": "Andrew", "accent": "US", "gender": "m"},
        {"id": "en-US-AvaNeural", "name": "Ava", "accent": "US", "gender": "f"},
        {"id": "en-GB-RyanNeural", "name": "Ryan", "accent": "UK", "gender": "m"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia", "accent": "UK", "gender": "f"},
    ],
    "fr": [
        {"id": "fr-FR-HenriNeural", "name": "Henri", "accent": "FR", "gender": "m"},
        {"id": "fr-FR-DeniseNeural", "name": "Denise", "accent": "FR", "gender": "f"},
    ],
    "es": [
        {"id": "es-ES-AlvaroNeural", "name": "Álvaro", "accent": "ES", "gender": "m"},
        {"id": "es-MX-DaliaNeural", "name": "Dalia", "accent": "MX", "gender": "f"},
    ],
    "de": [
        {"id": "de-DE-ConradNeural", "name": "Conrad", "accent": "DE", "gender": "m"},
        {"id": "de-DE-KatjaNeural", "name": "Katja", "accent": "DE", "gender": "f"},
    ],
    "tr": [
        {"id": "tr-TR-AhmetNeural", "name": "Ahmet", "accent": "TR", "gender": "m"},
        {"id": "tr-TR-EmelNeural", "name": "Emel", "accent": "TR", "gender": "f"},
    ],
}

_GENERATED = json.loads((Path(__file__).with_name("edge_voices.json")).read_text(encoding="utf-8"))
for _lang, _voices in _GENERATED["voices"].items():
    VOICES.setdefault(_lang, _voices)

# Piper pitch presets (the prototype's voice names keep working).
PIPER_VOICES = {"piper": 1.0, "natural": 1.0, "deep": 0.9, "female": 1.17}

# Characters per second at rate 0, used to estimate speech length before synthesizing.
# Measured per language with its default voice (edge_voices.json); Arabic keeps the value tuned by use.
# Languages written without spaces say far fewer characters per second (one character is a word).
CHARS_PER_SEC = {"edge": {**_GENERATED["cps"], "ar": 13, "default": 15}, "piper": {"ar": 11, "default": 11}}

LANG_LABEL = NAMES

_EDGE_ID = re.compile(r"^[a-z]{2,3}-[A-Z]{2}-\w+Neural$")


@dataclass(frozen=True)
class Voice:
    engine: str  # "edge" | "piper"
    voice: str
    lang: str
    pitch: float = 1.0

    @property
    def key(self) -> str:
        return f"{self.engine}|{self.voice}"


def voices_for(lang: str, piper_available: bool) -> list[dict[str, str]]:
    lang = target(lang)
    out = [{**v, "engine": "edge"} for v in VOICES.get(lang, VOICES["en"])]
    if lang == "ar" and piper_available:
        out.append({"id": "piper", "name": "كريم", "accent": "أوفلاين", "gender": "m", "engine": "piper"})
    return out


def resolve_voice(voice: str | None, lang: str | None) -> Voice:
    """``voice`` is an Edge voice id, a Piper preset, or ``auto``/``auto-m``/``auto-f``."""
    lang = target(lang)
    v = str(voice or "")
    if v in PIPER_VOICES and lang == "ar":
        return Voice("piper", "piper", lang, PIPER_VOICES[v])
    voices = VOICES.get(lang, VOICES["en"])
    if _EDGE_ID.match(v) and v.startswith(lang + "-"):
        return Voice("edge", v, lang)
    gender = "f" if v == "auto-f" else "m"
    pick = next((x for x in voices if x["gender"] == gender), voices[0])
    return Voice("edge", pick["id"], lang)


def alternatives(v: Voice, limit: int = 2) -> list[Voice]:
    """Up to ``limit`` other Microsoft voices of the same language, tried when one voice fails (Microsoft's
    service sometimes refuses a voice for a while): the same accent first (an Egyptian voice for an
    Egyptian one), then the same gender. Few, so a dead connection doesn't mean a dozen failures in a row."""
    if v.engine != "edge":
        return []
    region = v.voice.rsplit("-", 1)[0]  # "ar-EG"
    voices = VOICES.get(v.lang, [])
    me = next((x for x in voices if x["id"] == v.voice), None)
    rest = [x for x in voices if x["id"] != v.voice]
    rest.sort(key=lambda x: (not x["id"].startswith(region + "-"), bool(me) and x["gender"] != me["gender"]))
    return [Voice("edge", x["id"], v.lang) for x in rest[:limit]]
