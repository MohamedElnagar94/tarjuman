"""Offline translation: routing between installed models, the fallback when Google refuses, the API."""

import asyncio

from tarjuman.translate.local import PAIRS, LocalMT
from tarjuman.translate.service import Translator


def _fake_install(mt: LocalMT, pair: str) -> None:
    p = mt.path(pair)
    p.mkdir(parents=True, exist_ok=True)
    for f in ("model.bin", "source.spm", "target.spm"):
        (p / f).write_bytes(b"x")


def test_official_models_cover_english_both_ways():
    assert {"en-ar", "en-fr", "en-zh", "en-ru"} <= set(PAIRS)
    assert {"ar-en", "zh-en", "ja-en"} <= set(PAIRS)
    assert all(u.startswith("https://object.pouta.csc.fi/") for u in PAIRS.values())


def test_routes_go_direct_or_through_english(tmp_path):
    mt = LocalMT(tmp_path / "opus", tmp_path / "mt.json")
    assert mt.route("en", "ar") is None
    _fake_install(mt, "en-ar")
    assert mt.route("en", "ar") == ["en-ar"]
    assert mt.route("auto", "ar", ["Hello there"]) == ["en-ar"]
    assert mt.route("auto", "ar", ["你好世界"]) is None  # unknown non-Latin source: not guessed
    _fake_install(mt, "zh-en")
    assert mt.route("zh", "ar") == ["zh-en", "en-ar"]
    mt.delete("en-ar")
    assert mt.route("zh", "ar") is None


def test_preference_is_saved(tmp_path):
    mt = LocalMT(tmp_path / "opus", tmp_path / "mt.json")
    mt.set_prefer("offline")
    again = LocalMT(tmp_path / "opus", tmp_path / "mt.json")
    again.load()
    assert again.prefer == "offline"


class _FakeLocal:
    prefer = "online"

    async def translate(self, texts, sl, tl):
        return ["محلي: " + t for t in texts]


def _translator(tmp_path, local):
    tr = Translator(tmp_path / "c.json", tmp_path / "e.json", local)
    tr.load()
    return tr


def test_this_computer_translates_when_google_refuses_and_its_lines_are_not_kept(tmp_path):
    tr = _translator(tmp_path, _FakeLocal())

    async def down(*a, **k):
        raise RuntimeError("no internet")

    for g in tr.googles:
        g.translate_batch = down
        g.translate = down
    tr.mymemory.translate = down
    got = asyncio.run(tr.translate_many(["Hello."], sl="en", tl="ar"))
    assert got == {"Hello.": "محلي: Hello."}
    assert tr.stats["lastProvider"] == "local"
    assert not tr.cache, "a Google translation must replace it once the internet is back"


def test_offline_preference_skips_google(tmp_path):
    local = _FakeLocal()
    local.prefer = "offline"
    tr = _translator(tmp_path, local)

    async def must_not_call(*a, **k):
        raise AssertionError("Google was asked although the user chose offline")

    for g in tr.googles:
        g.translate_batch = must_not_call
    assert asyncio.run(tr.translate_many(["Hi."], sl="en", tl="ar")) == {"Hi.": "محلي: Hi."}

