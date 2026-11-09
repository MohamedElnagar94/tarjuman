"""The voices: Microsoft neural voices (free, online) and Piper (offline, Arabic)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..core.text import norm_lang

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

# Piper pitch presets (the prototype's voice names keep working).
PIPER_VOICES = {"piper": 1.0, "natural": 1.0, "deep": 0.9, "female": 1.17}

# Characters per second at rate 0, used to estimate speech length before synthesizing.
CHARS_PER_SEC = {"edge": {"ar": 13, "default": 15}, "piper": {"ar": 11, "default": 11}}

LANG_LABEL = {"ar": "Arabic", "en": "English", "fr": "French", "es": "Spanish", "de": "German", "tr": "Turkish"}

_EDGE_ID = re.compile(r"^[a-z]{2}-[A-Z]{2}-\w+Neural$")


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
    lang = norm_lang(lang) or "ar"
    out = [{**v, "engine": "edge"} for v in VOICES.get(lang, VOICES["en"])]
    if lang == "ar" and piper_available:
        out.append({"id": "piper", "name": "كريم", "accent": "أوفلاين", "gender": "m", "engine": "piper"})
    return out


def resolve_voice(voice: str | None, lang: str | None) -> Voice:
    """``voice`` is an Edge voice id, a Piper preset, or ``auto``/``auto-m``/``auto-f``."""
    lang = norm_lang(lang) or "ar"
    v = str(voice or "")
    if v in PIPER_VOICES and lang == "ar":
        return Voice("piper", "piper", lang, PIPER_VOICES[v])
    voices = VOICES.get(lang, VOICES["en"])
    if _EDGE_ID.match(v) and v.startswith(lang + "-"):
        return Voice("edge", v, lang)
    gender = "f" if v == "auto-f" else "m"
    pick = next((x for x in voices if x["gender"] == gender), voices[0])
    return Voice("edge", pick["id"], lang)
