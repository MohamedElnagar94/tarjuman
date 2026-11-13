"""Recordings: telling audio from video, the waveform, the Whisper settings and recommendation, and
cutting long Whisper segments into sentences."""

import io
import math
import struct
import wave
from types import SimpleNamespace

from fastapi.testclient import TestClient

from tarjuman.api.app import create_app
from tarjuman.asr import split_sentences
from tarjuman.asr_settings import AsrSettings, recommend
from tarjuman.media.probe import peaks, probe, small_peaks
from tarjuman.services import Services

LOCAL = {"host": "127.0.0.1:4318"}
OCTET = {"content-type": "application/octet-stream"}


def tone_wav(seconds=2.0, rate=16000) -> bytes:
    """A tone that is loud in its first half and quiet in its second."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        frames = b"".join(
            struct.pack("<h", int((12000 if i < n / 2 else 1500) * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n)
        )
        w.writeframes(frames)
    return buf.getvalue()


HW_LAPTOP = {"threads": 8, "cores": 4, "ramGb": 16, "cuda": 1, "gpu": "Quadro M2000M", "vramGb": 4, "cublas": False}
HW_GPU = {"threads": 8, "cores": 4, "ramGb": 16, "cuda": 1, "gpu": "RTX 4070", "vramGb": 12, "cublas": True}
HW_SMALL = {"threads": 2, "cores": 2, "ramGb": 4, "cuda": 0, "gpu": "", "vramGb": 0, "cublas": False}


def test_the_recommendation_follows_the_computer_and_says_why():
    laptop = recommend(HW_LAPTOP)
    assert laptop["device"] == "cpu" and laptop["model"] == "small" and laptop["short"] == "large-v3"
    assert any("cuBLAS" in w for w in laptop["why"]), "a card that can't be used is explained"
    assert recommend(HW_GPU)["model"] == "large-v3" and recommend(HW_GPU)["device"] == "cuda"
    assert recommend(HW_SMALL)["model"] == "base"


def test_auto_gives_a_short_recording_the_more_accurate_model(tmp_path):
    s = AsrSettings(tmp_path / "asr.json")
    assert s.effective(HW_LAPTOP, duration=40)["model"] == "large-v3"
    assert s.effective(HW_LAPTOP, duration=1800)["model"] == "small"
    s.update({"model": "medium", "language": "ar", "quality": "fast"})
    eff = s.effective(HW_LAPTOP, duration=40)
    assert eff["model"] == "medium", "a model the user picked always wins"
    assert eff["language"] == "ar" and eff["beam"] == 1 and eff["device"] == "cpu"
    s.update({"device": "cuda"})
    assert s.effective(HW_LAPTOP)["device"] == "cpu", "a card CUDA can't use is never chosen"
    assert s.effective(HW_GPU)["device"] == "cuda"


def test_bad_settings_are_ignored(tmp_path):
    s = AsrSettings(tmp_path / "asr.json")
    s.update({"model": "huge", "language": "klingon", "style": "pirate", "device": "tpu"})
    assert s.values["model"] == "auto" and s.values["language"] == "auto"
    assert s.values["style"] == "general" and s.values["device"] == "auto"
    assert AsrSettings(tmp_path / "asr.json").load().values == s.values


def word(text, start, end):
    return SimpleNamespace(word=text, start=start, end=end)


def test_a_long_segment_is_cut_into_sentences_with_their_own_times():
    words = [word(" السلام", 0.0, 0.5), word(" عليكم.", 0.5, 1.0), word(" أريد", 1.4, 1.8), word(" أن", 1.8, 2.0),
             word(" أحجز", 2.0, 2.5), word(" موعدًا.", 2.5, 3.2), word(" هل", 3.6, 3.8), word(" هذا", 3.8, 4.0),
             word(" ممكن؟", 4.0, 4.6)]
    seg = SimpleNamespace(start=0.0, end=4.6, text="".join(w.word for w in words), words=words)
    out = split_sentences(seg)
    assert [s["text"] for s in out] == ["السلام عليكم.", "أريد أن أحجز موعدًا.", "هل هذا ممكن؟"]
    assert out[1]["start"] == 1.4 and out[1]["end"] == 3.2


def test_a_segment_without_word_times_stays_whole():
    seg = SimpleNamespace(start=1.0, end=2.0, text=" مرحبا", words=None)
    assert split_sentences(seg) == [{"start": 1.0, "end": 2.0, "text": "مرحبا"}]


def test_probe_and_waveform(tmp_path):
    f = tmp_path / "note.wav"
    f.write_bytes(tone_wav())
    assert probe(f) == {"kind": "audio", "duration": 2.0}
    p = peaks(f, buckets=100)
    assert abs(p["duration"] - 2.0) < 0.05 and len(p["peaks"]) == 100
    first, second = p["peaks"][:45], p["peaks"][55:]
    assert min(first) > 0.8 and max(second) < 0.3, "the loud half is drawn loud, the quiet half quiet"
    assert len(small_peaks(p["peaks"], 48)) == 48


def test_an_uploaded_recording_is_known_as_audio_and_can_be_transcribed_again(tmp_path):
    s = Services()
    app = create_app(s, warm=False)
    with TestClient(app, headers=LOCAL, client=("127.0.0.1", 50000)) as c:
        r = c.post("/api/media/upload?name=voice note.wav", content=tone_wav(), headers=OCTET).json()
        assert r["ok"] and r["kind"] == "audio" and r["duration"] == 2.0
        mid = r["id"]
        w = c.get(f"/api/media/peaks?id={mid}").json()
        assert w["ok"] and len(w["peaks"]) > 50
        listed = c.get("/api/media").json()["items"]
        assert listed[0]["wave"] and len(listed[0]["wave"]) == 48, "the library shows a small waveform"

        m = s.media.get(mid)
        m.segments, m.lang, m.asr = [{"start": 0, "end": 1, "text": "مرحبا"}], "ar", "small"
        s.media.save()
        assert c.get(f"/api/cues?url=media:{mid}&tl=ar").json()["cues"][0]["src"] == "مرحبا"
        assert c.post("/api/media/retranscribe", json={"id": mid}).json()["ok"]
        assert c.get(f"/api/cues?url=media:{mid}&tl=ar").json()["code"] == "NO_CAPTIONS"
        assert c.get(f"/api/media/info?id={mid}").json()["asr"] == ""


def test_the_settings_api_explains_the_computer(tmp_path):
    s = Services()
    app = create_app(s, warm=False)
    with TestClient(app, headers=LOCAL, client=("127.0.0.1", 50000)) as c:
        j = c.get("/api/asr?duration=60").json()
        assert j["ok"] and {"settings", "hardware", "recommended", "effective", "models", "status"} <= set(j)
        assert [m["id"] for m in j["models"]][:2] == ["tiny", "base"]
        j = c.post("/api/asr", json={"model": "small", "style": "egyptian"}).json()
        assert j["settings"]["model"] == "small" and j["effective"]["model"] == "small"
        assert "مصرية" in j["effective"]["prompt"]


def test_the_app_window_gives_its_own_page_the_microphone_back(tmp_path):
    import json

    from tarjuman.desktop import allow_microphone

    prefs = tmp_path / "Default" / "Preferences"
    prefs.parent.mkdir(parents=True)
    other = {"https://example.com:443,*": {"last_modified": "1", "setting": 2}}
    blocked = {"http://127.0.0.1:4318,*": {"last_modified": "1", "setting": 2}, **other}
    prefs.write_text(json.dumps({"profile": {"content_settings": {"exceptions": {"media_stream_mic": blocked}}}, "x": 1}))
    assert allow_microphone("http://127.0.0.1:4318/", tmp_path)
    data = json.loads(prefs.read_text())
    mic = data["profile"]["content_settings"]["exceptions"]["media_stream_mic"]
    assert mic["http://127.0.0.1:4318,*"]["setting"] == 1
    assert mic["https://example.com:443,*"]["setting"] == 2, "other sites are left alone"
    assert data["x"] == 1, "the rest of the browser's preferences are kept"
    prefs.write_text("{broken")
    assert not allow_microphone("http://127.0.0.1:4318/", tmp_path)
    assert prefs.read_text() == "{broken", "a file it can't read is never overwritten"


def test_quit_is_only_for_the_computer_and_only_for_the_desktop_app():
    app = create_app(Services(), warm=False)
    with TestClient(app, headers=LOCAL, client=("127.0.0.1", 50000)) as c:
        assert c.post("/api/desktop/quit", json={}).json() == {"ok": True, "quitting": False}
    remote = TestClient(app, base_url="http://192.168.0.104:4318", headers={"host": "192.168.0.104:4318"}, client=("192.168.0.20", 50000))
    assert remote.post("/api/desktop/quit", json={}).status_code in (401, 403)


def test_a_downloaded_model_can_be_deleted_to_free_the_disk(tmp_path, monkeypatch):
    from tarjuman import asr_settings as a

    monkeypatch.setenv("HF_HOME", str(tmp_path))
    repo = tmp_path / "hub" / "models--Systran--faster-whisper-small"
    (repo / "snapshots" / "abc").mkdir(parents=True)
    (repo / "snapshots" / "abc" / "model.bin").write_bytes(b"x" * 5000)
    (repo / "snapshots" / "abc" / "config.json").write_text("{}")
    other = tmp_path / "hub" / "models--Systran--faster-whisper-base" / "snapshots" / "d"
    other.mkdir(parents=True)
    (other / "model.bin").write_bytes(b"y" * 100)
    assert a.model_disk_bytes("small") == 5002
    assert a.delete_model("small") == 5002
    assert not repo.exists() and (other / "model.bin").exists(), "only that model is removed"
    assert a.delete_model("not-a-model") == 0


def test_the_names_list_becomes_a_hint_for_whisper(tmp_path):
    from tarjuman.asr_settings import vocab_words

    assert vocab_words("كريم\nExcel، Zoom, كريم\n\n") == "كريم، Excel، Zoom"
    s = AsrSettings(tmp_path / "asr.json")
    s.update({"vocab": "كريم\nZoom"})
    assert s.effective(HW_LAPTOP)["hotwords"] == "كريم، Zoom"


def test_an_old_card_is_not_recommended_even_with_cuda():
    old = {**HW_GPU, "gpu": "Quadro M2000M", "vramGb": 4, "computeCap": 5.0, "gpuOld": True}
    r = recommend(old)
    assert r["device"] == "cpu" and any("قديم" in w for w in r["why"])


async def test_the_ai_fix_keeps_every_line_in_place():
    from tarjuman.ai.transcript_fix import fix_lines

    class Fake:
        def __init__(self, answer):
            self.answer = answer

        async def complete(self, system, user, **_):
            assert "dialect" in system and "كريم" in system
            return self.answer

    lines = ["ابعتلي الملف على الإكسيل يا كريب", "وبعدين نتكلم"]
    got = await fix_lines(Fake({"lines": ["1. ابعتلي الملف على Excel يا كريم", "وبعدين نتكلم"]}), lines, "ar", "كريم")
    assert got == ["ابعتلي الملف على Excel يا كريم", "وبعدين نتكلم"]
    assert await fix_lines(Fake({"lines": ["سطر واحد فقط"]}), lines, "ar", "كريم") == lines, "a wrong count changes nothing"
