"""Voice packs: shown only where they make sense, never installed without the licence, never half-used."""

import asyncio

import pytest

from tarjuman.core.errors import AppError
from tarjuman.engines.packs import PACKS, Packs, strong_gpu
from tarjuman.voice.catalog import Voice


def test_strong_gpu_means_a_modern_nvidia_card_with_memory():
    assert strong_gpu({"cuda": True, "computeCap": 8.6, "vramGb": 12})
    assert not strong_gpu({"cuda": True, "computeCap": 5.0, "vramGb": 4})  # a 2016 Quadro M2000M
    assert not strong_gpu({"cuda": True, "computeCap": 8.6, "vramGb": 4})
    assert not strong_gpu({})


def test_xtts_needs_its_licence_accepted_before_installing(tmp_path):
    packs = Packs(tmp_path)
    x = packs.get("xtts")
    assert not x.accepted
    with pytest.raises(AppError) as e:
        asyncio.run(x.install(gpu=False))
    assert e.value.code == "LICENCE_NOT_ACCEPTED"
    x.accept()
    assert x.accepted and x._env()["COQUI_TOS_AGREED"] == "1"
    assert "COQUI_TOS_AGREED" not in packs.get("habibi")._env(), "Apache-licensed: nothing to accept"


def test_status_lists_both_packs_with_their_languages(tmp_path):
    st = Packs(tmp_path).status({"cuda": False})
    assert {p["name"] for p in st["packs"]} == {"xtts", "habibi"}
    assert st["strongGpu"] is False
    assert "ar" in PACKS["xtts"]["langs"] and "ja" in PACKS["xtts"]["langs"]


def test_a_pack_voice_without_the_pack_is_an_error_not_a_silent_other_voice(tmp_path):
    from tarjuman.services import Services

    s = Services()
    s.packs = Packs(tmp_path)
    s.tts.packs = s.packs
    with pytest.raises(AppError) as e:
        asyncio.run(s.tts.synth_wav("مرحبا", Voice("habibi", "EGY", "ar"), 0, tmp_path / "x.wav"))
    assert e.value.code == "PACK_NOT_INSTALLED"
