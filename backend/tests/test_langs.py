"""Every target language: a translation code, voices that exist, a speaking speed, and a font when burned in."""

from tarjuman.core import langs
from tarjuman.media.mixer import burn_style
from tarjuman.voice.catalog import CHARS_PER_SEC, VOICES, alternatives, resolve_voice


def test_every_language_has_voices_a_speed_and_an_mp4_code():
    assert len(langs.NAMES) >= 70
    for code in langs.NAMES:
        voices = VOICES.get(code)
        assert voices, f"{code} has no voice"
        assert all(v["id"].startswith(code + "-") for v in voices), code
        assert {v["gender"] for v in voices} <= {"m", "f"}
        assert CHARS_PER_SEC["edge"].get(code), f"{code} has no speaking speed"
        assert langs.ISO3.get(code), code


def test_codes_are_mapped_for_each_service():
    assert langs.google_code("zh") == "zh-CN" and langs.google_code("he") == "iw" and langs.google_code("ja") == "ja"
    assert langs.target("zh-TW") == "zh" and langs.target("iw") == "he" and langs.target("tl") == "fil"
    assert langs.target("klingon") == "ar"


def test_languages_without_spaces_speak_fewer_characters_a_second():
    cps = CHARS_PER_SEC["edge"]
    assert cps["zh"] < 8 and cps["ja"] < 8 and cps["ko"] < 9 and cps["en"] > 12


def test_a_failing_voice_has_a_fallback_of_the_same_accent():
    v = resolve_voice("ar-EG-ShakirNeural", "ar")
    assert alternatives(v)[0].voice == "ar-EG-SalmaNeural"
    assert all(a.lang == "ja" for a in alternatives(resolve_voice("auto", "ja")))


def test_burned_subtitles_use_a_font_with_the_letters():
    assert "Yu Gothic" in burn_style("ja") and "Arial" in burn_style("fr")
