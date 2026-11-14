"""The languages Tarjuman translates and dubs into: every language Microsoft's neural voices speak.

Codes are ISO 639-1 (``fil`` for Filipino). Names are in English, for prompts to AI models; the interface
shows each name in the user's own language (Intl.DisplayNames)."""

from __future__ import annotations

from .text import norm_lang

NAMES: dict[str, str] = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "az": "Azerbaijani", "bg": "Bulgarian", "bn": "Bengali",
    "bs": "Bosnian", "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "es": "Spanish", "et": "Estonian", "fa": "Persian", "fi": "Finnish", "fil": "Filipino",
    "fr": "French", "ga": "Irish", "gl": "Galician", "gu": "Gujarati", "he": "Hebrew", "hi": "Hindi", "hr": "Croatian",
    "hu": "Hungarian", "id": "Indonesian", "is": "Icelandic", "it": "Italian", "ja": "Japanese", "jv": "Javanese",
    "ka": "Georgian", "kk": "Kazakh", "km": "Khmer", "kn": "Kannada", "ko": "Korean", "lo": "Lao", "lt": "Lithuanian",
    "lv": "Latvian", "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi", "ms": "Malay",
    "mt": "Maltese", "my": "Burmese", "nb": "Norwegian", "ne": "Nepali", "nl": "Dutch", "pl": "Polish", "ps": "Pashto",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian",
    "so": "Somali", "sq": "Albanian", "sr": "Serbian", "su": "Sundanese", "sv": "Swedish", "sw": "Swahili",
    "ta": "Tamil", "te": "Telugu", "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu", "uz": "Uzbek",
    "vi": "Vietnamese", "zh": "Chinese", "zu": "Zulu",
}

RTL = {"ar", "fa", "he", "ps", "ur"}

# Written without spaces between words: no word wrapping at spaces, and sentences end with "。" or "।".
NO_SPACES = {"ja", "zh", "th", "lo", "km", "my"}

# ISO 639-2 codes, for the language of a track inside an MP4.
ISO3: dict[str, str] = {
    "af": "afr", "am": "amh", "ar": "ara", "az": "aze", "bg": "bul", "bn": "ben", "bs": "bos", "ca": "cat", "cs": "ces",
    "cy": "cym", "da": "dan", "de": "deu", "el": "ell", "en": "eng", "es": "spa", "et": "est", "fa": "fas", "fi": "fin",
    "fil": "fil", "fr": "fra", "ga": "gle", "gl": "glg", "gu": "guj", "he": "heb", "hi": "hin", "hr": "hrv", "hu": "hun",
    "id": "ind", "is": "isl", "it": "ita", "ja": "jpn", "jv": "jav", "ka": "kat", "kk": "kaz", "km": "khm", "kn": "kan",
    "ko": "kor", "lo": "lao", "lt": "lit", "lv": "lav", "mk": "mkd", "ml": "mal", "mn": "mon", "mr": "mar", "ms": "msa",
    "mt": "mlt", "my": "mya", "nb": "nob", "ne": "nep", "nl": "nld", "pl": "pol", "ps": "pus", "pt": "por", "ro": "ron",
    "ru": "rus", "si": "sin", "sk": "slk", "sl": "slv", "so": "som", "sq": "sqi", "sr": "srp", "su": "sun", "sv": "swe",
    "sw": "swa", "ta": "tam", "te": "tel", "th": "tha", "tr": "tur", "uk": "ukr", "ur": "urd", "uz": "uzb", "vi": "vie",
    "zh": "zho", "zu": "zul",
}

# A font with the language's letters, for subtitles burned into a video (libass falls back to these
# names on Windows; elsewhere it finds whatever font covers the script).
BURN_FONT = {
    "ja": "Yu Gothic", "zh": "Microsoft YaHei", "ko": "Malgun Gothic", "th": "Leelawadee UI", "lo": "Leelawadee UI",
    "km": "Leelawadee UI", "my": "Myanmar Text", "hi": "Nirmala UI", "mr": "Nirmala UI", "ne": "Nirmala UI",
    "bn": "Nirmala UI", "gu": "Nirmala UI", "ta": "Nirmala UI", "te": "Nirmala UI", "kn": "Nirmala UI", "ml": "Nirmala UI",
    "si": "Nirmala UI", "am": "Ebrima", "ka": "Sylfaen", "he": "Arial", "ar": "Arial", "fa": "Arial", "ur": "Arial",
}

# Google Translate's own codes where they differ.
_GOOGLE = {"zh": "zh-CN", "he": "iw", "fil": "tl", "nb": "no", "jv": "jw"}
# MyMemory takes regional codes for these.
_MYMEMORY = {"zh": "zh-CN", "fil": "tl", "nb": "no"}


def target(lang: str | None, default: str = "ar") -> str:
    """A supported target language for ``lang`` (``zh-TW`` -> ``zh``, ``tl`` -> ``fil``), or ``default``."""
    raw = str(lang or "").strip().lower().replace("_", "-")
    if raw in NAMES:
        return raw
    base = norm_lang(raw)
    base = {"tl": "fil", "iw": "he", "no": "nb", "jw": "jv"}.get(base, base)
    return base if base in NAMES else default


def google_code(lang: str) -> str:
    return _GOOGLE.get(lang, lang)


def mymemory_code(lang: str) -> str:
    return _MYMEMORY.get(lang, lang)


def name(lang: str) -> str:
    return NAMES.get(lang, lang)
