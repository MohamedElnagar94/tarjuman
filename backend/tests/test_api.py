"""The HTTP API, offline: translation and voices are replaced by fakes."""

import re

import pytest
from fastapi.testclient import TestClient

from tarjuman.api.app import create_app
from tarjuman.services import Services
from tarjuman.voice.service import TtsResult

LOCAL = {"host": "127.0.0.1:4318"}


@pytest.fixture()
def services():
    s = Services()

    async def fake_translate_many(texts, sl="auto", tl="ar", **_):
        return {t: "ع:" + t for t in texts if t}

    async def fake_speak(text, lang="ar", voice="", rate=0, *, priority=2):
        # 14 characters per second at rate 0, like a real voice.
        return TtsResult(b"ID3fake", "audio/mpeg", round(len(text) / 14 / (1 + float(rate) / 100), 3), "edge")

    s.translator.translate_many = fake_translate_many
    s.tts.speak = fake_speak
    return s


@pytest.fixture()
def app(services):
    a = create_app(services, warm=False)
    a.state.extensions.allowed, a.state.extensions.pending = [], []  # each test starts with no trusted extension
    a.state.pairing.devices = []  # ...and no paired device
    return a


@pytest.fixture()
def client(app):
    """Requests from the computer running the app."""
    with TestClient(app, headers=LOCAL, client=("127.0.0.1", 50000)) as c:
        yield c


@pytest.fixture()
def phone(app):
    """Requests from another device on the Wi-Fi."""
    with TestClient(app, base_url="http://192.168.0.104:4318", headers={"host": "192.168.0.104:4318"},
                    client=("192.168.0.50", 50000), follow_redirects=False) as c:
        yield c


def test_health_identifies_the_app(client):
    j = client.get("/api/health").json()
    assert j["ok"] and j["app"] == "tarjuman"
    assert "whisper" in j and "tts" in j and "ai" in j


def test_cross_site_requests_and_rebinding_are_refused(client):
    assert client.get("/api/health", headers={"origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/health", headers={"host": "evil.example:4318"}).status_code == 403
    assert client.get("/api/health", headers={"origin": "chrome-extension://abc"}).status_code == 200


def test_posts_must_be_json(client):
    r = client.post("/api/vocab", content="word=x", headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415
    assert r.json()["code"] == "JSON_REQUIRED"


def test_settings_answer_only_to_this_computer(phone):
    r = phone.get("/api/settings")
    assert r.status_code == 403 and r.json()["code"] == "LOCAL_ONLY"
    assert phone.get("/api/pairing").status_code == 403, "a phone can't read the pairing code"


ANDROID = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"


def other_device(app, ip, ua):
    return TestClient(app, base_url="http://192.168.0.104:4318", headers={"host": "192.168.0.104:4318", "user-agent": ua},
                      client=(ip, 50000), follow_redirects=False)


def test_another_device_needs_pairing_before_it_can_use_the_app(app, phone):
    assert phone.get("/api/vocab").status_code == 401
    assert phone.get("/api/library").json()["code"] == "NOT_PAIRED"
    assert phone.get("/api/health").json()["paired"] is False, "health still answers, to show the pairing screen"
    assert phone.get("/pair?code=wrong").status_code == 403
    r = phone.get("/pair?code=" + app.state.pairing.code)
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert "tarjuman_pair" in r.headers["set-cookie"] and "httponly" in r.headers["set-cookie"].lower()
    assert phone.get("/api/vocab").json()["ok"], "the cookie pairs this browser"
    assert phone.get("/api/health").json()["paired"] is True


def test_each_phone_gets_its_own_key_and_can_be_unpaired_alone(app, client):
    with other_device(app, "192.168.0.50", ANDROID) as a, other_device(app, "192.168.0.51", IPHONE) as b:
        a.get("/pair?code=" + app.state.pairing.code)
        b.get("/pair?code=" + app.state.pairing.code)
        a.get("/pair?code=" + app.state.pairing.code)  # scanning twice doesn't list it twice
        devices = client.get("/api/pairing").json()["devices"]
        assert sorted(d["name"] for d in devices) == ["Android · SM-S918B · Chrome", "iPhone · Safari"]
        android = next(d for d in devices if d["name"].startswith("Android"))
        assert android["lastIp"] == "192.168.0.50"
        client.post("/api/pairing/device", json={"id": android["id"], "action": "remove"})
        assert a.get("/api/vocab").status_code == 401, "the removed phone is out"
        assert b.get("/api/vocab").status_code == 200, "the other one stays paired"
        iphone = client.get("/api/pairing").json()["devices"][0]
        client.post("/api/pairing/device", json={"id": iphone["id"], "action": "rename", "name": "هاتف أمي"})
        assert client.get("/api/pairing").json()["devices"][0]["name"] == "هاتف أمي"


def test_a_new_code_stops_the_old_qr_but_keeps_paired_phones(app, client, phone):
    old = app.state.pairing.code
    phone.get("/pair?code=" + old)
    client.post("/api/pairing/reset", json={})
    assert phone.get("/api/vocab").status_code == 200, "already paired: still in"
    with other_device(app, "192.168.0.60", IPHONE) as late:
        assert late.get("/pair?code=" + old).status_code == 403, "the old QR no longer pairs"


def test_unpairing_all_devices_also_retires_the_qr(app, client, phone):
    old = app.state.pairing.code
    phone.get("/pair?code=" + old)
    client.post("/api/pairing/unpair-all", json={})
    assert phone.get("/api/vocab").status_code == 401
    assert client.get("/api/pairing").json()["devices"] == []
    assert phone.get("/pair?code=" + old).status_code == 403


def test_a_phone_paired_by_the_first_version_keeps_working_and_gets_its_own_key(app, client, phone):
    legacy = app.state.pairing.code
    app.state.pairing._legacy = legacy  # what the first version's cookie held
    phone.cookies.set("tarjuman_pair", legacy)
    r = phone.get("/api/vocab")
    assert r.status_code == 200 and "tarjuman_pair" in r.headers.get("set-cookie", "")
    assert len(client.get("/api/pairing").json()["devices"]) == 1


def test_this_computer_never_needs_pairing(client):
    assert client.get("/api/vocab").status_code == 200
    assert client.get("/api/health").json()["paired"] is True


def test_uploads_are_capped_and_cleaned_up(client, services, monkeypatch):
    from tarjuman import config

    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1000)
    r = client.post("/api/media/upload?name=a.mp4", content=b"x" * 5000, headers={"content-type": "application/octet-stream"})
    assert r.status_code == 413 and r.json()["code"] == "UPLOAD_TOO_LARGE"
    assert services.media.items == {}, "nothing left behind"
    r = client.post("/api/media/upload?name=a.mp4", content=b"x" * 500, headers={"content-type": "application/octet-stream"})
    assert r.json()["ok"] and r.json()["size"] == 500


def test_settings_never_return_the_key_and_clear_it_when_the_provider_changes(services):
    services.ai.update({"enabled": True, "provider": "openai", "baseUrl": "https://a.example/v1", "model": "m", "apiKey": "sk-secret-1234"})
    pub = services.ai.public()["ai"]
    assert pub["hasKey"] and pub["keyHint"] == "…1234"
    assert "sk-secret" not in str(pub)
    services.ai.update({"baseUrl": "https://b.example/v1"})
    assert services.ai.ai["apiKey"] == "", "a key is never sent to a server it wasn't entered for"


def test_bad_json_is_a_400(client):
    r = client.post("/api/vocab", content="{nope", headers={"content-type": "application/json"})
    assert r.status_code == 400 and r.json()["code"] == "BAD_JSON"


def test_vocab_add_dedupe_delete_and_anki_export(client):
    r = client.post("/api/vocab", json={"word": "Engine", "tr": "محرك", "sentence": "The engine runs.", "t": 3})
    item = r.json()["item"]
    assert not r.json()["duplicate"]
    assert client.post("/api/vocab", json={"word": "engine", "sentence": "The engine runs."}).json()["duplicate"]
    csv = client.get("/api/vocab.csv").text
    assert "Engine<br><small>The engine runs.</small>" in csv
    client.post("/api/vocab/delete", json={"id": item["id"]})
    assert client.get("/api/vocab").json()["items"] == []


def test_pronunciation_dictionary_applies_to_whole_words_only(client):
    client.post("/api/pronounce", json={"items": [{"from": "UE5", "to": "أنريل إنجن فايف"}, {"from": "", "to": "x"}]})
    assert len(client.get("/api/pronounce").json()["items"]) == 1
    out = client.post("/api/pronounce/preview", json={"text": "Open UE5 now, not UE55."}).json()["text"]
    assert out == "Open أنريل إنجن فايف now, not UE55."


def test_dub_plan_for_site_captions_is_paced_and_measured(client):
    cues = [
        {"start": 0, "end": 2, "src": "what are AI's strengths and"},
        {"start": 2, "end": 3, "src": "limitations so you know when to use it."},
        {"start": 3.1, "end": 6, "src": "As a test, I made three games."},
    ]
    j = client.post("/api/dubplan/cues", json={"cues": cues, "tl": "ar", "from": 0, "to": 30, "urgent": True}).json()
    assert j["ok"] and j["total"] == 2
    b0 = j["blocks"][0]
    assert b0["text"].startswith("ع:") and "strengths and limitations" in b0["src"]
    for b in j["blocks"]:
        assert {"i", "start", "slot", "rate", "synthRate", "playRate", "text"} <= b.keys()
        assert 0.85 <= b["playRate"] <= 1.2
        assert -30 <= b["synthRate"] <= 80


def test_dub_plan_needs_cues(client):
    j = client.post("/api/dubplan/cues", json={"cues": [], "tl": "ar"}).json()
    assert not j["ok"] and j["code"] == "NO_CUES"


def test_unknown_job_and_file(client):
    assert client.get("/api/dub/job?id=nope").json()["code"] == "NO_JOB"
    assert client.get("/api/library/file?kind=subs&name=../secret.txt").status_code == 404


def test_translate_edit_wins_over_machine_translation(client, services):
    client.post("/api/translate/edit", json={"src": "Hello", "ar": "أهلًا بيكم", "tl": "ar"})
    assert services.translator.lookup("ar", "Hello") == "أهلًا بيكم"
    client.post("/api/translate/edit", json={"src": "Hello", "ar": "", "tl": "ar"})
    assert services.translator.lookup("ar", "Hello") is None


def test_spa_fallback_serves_a_page_for_client_routes(client):
    r = client.get("/watch?url=abc")
    assert r.status_code == 200 and "<html" in r.text.lower()
    assert client.get("/api/nope").status_code == 404


def test_web_app_files_get_browser_mime_types(client):
    import mimetypes

    # Browsers refuse module scripts served as text/plain (the Windows registry default for .js).
    assert mimetypes.guess_type("index-abc.js")[0] == "text/javascript"
    assert mimetypes.guess_type("font.woff2")[0] == "font/woff2"
    r = client.get("/dub-engine.js")
    assert r.headers["content-type"].startswith("text/javascript")


async def test_dub_falls_back_to_youtubes_translation_when_translators_refuse(services):
    from tarjuman.captions.models import Cue, Line, VideoCues
    from tarjuman.dub.live import Plan
    from tarjuman.dub.planner import group_dub_blocks

    async def refuse(texts, **_):
        return {}  # Google rate-limited and MyMemory out of quota

    async def youtube_lines(video_id, tl):
        return [Line(0, 2.5, "أهلًا بالجميع"), Line(2.5, 4, "في الدرس الأول"), Line(6, 9, "لنبدأ الآن")]

    services.translator.translate_many = refuse
    services.captions.youtube_translation = youtube_lines
    cues = [Cue(0, 4, "hi everyone and welcome to the first lesson"), Cue(6, 9, "let's start now")]
    data = VideoCues(videoId="abcdefghijk", title="t", author="", lengthSeconds=9, tl="ar",
                     alreadyTranslated=False, asr=True, srcLang="en", cues=cues)
    plan = Plan(data, False, "en", group_dub_blocks(cues))
    blocks = await services.live.blocks(plan, 0, 10, "", "ar")
    plain = [re.sub("[ً-ْ]", "", b["text"]) for b in blocks]  # the voice text may carry diacritics
    assert plain == ["أهلا بالجميع في الدرس الأول", "لنبدأ الآن"]


def test_the_first_extension_is_trusted_and_others_wait_for_approval(client):
    mine = {"origin": "chrome-extension://tarjumanaaaa"}
    other = {"origin": "chrome-extension://somethingelse"}
    assert client.get("/api/health", headers=mine).status_code == 200
    assert client.get("/api/health", headers=other).json()["extensionAllowed"] is False, "health says why"
    r = client.get("/api/vocab", headers=other)
    assert r.status_code == 403 and r.json()["code"] == "EXTENSION_NOT_ALLOWED"
    assert client.get("/api/extensions").json()["pending"] == ["somethingelse"]
    client.post("/api/extensions/set", json={"id": "somethingelse", "allow": True})
    assert client.get("/api/vocab", headers=other).status_code == 200
    client.post("/api/extensions/set", json={"id": "somethingelse", "allow": False})
    assert client.get("/api/vocab", headers=other).status_code == 403


def test_storage_reports_sizes_and_clears_caches_but_never_corrections(client, services, phone):
    from tarjuman import config

    (config.TTS_DIR / "abc.mp3").write_bytes(b"x" * 2048)
    services.translator.cache["ar|hello"] = "مرحبا"
    services.translator.set_edit("ar", "Hi", "أهلًا")
    u = client.get("/api/storage").json()["usage"]
    assert u["voices"]["bytes"] >= 2048 and {"dubbed", "media", "models", "tmp"} <= u.keys()
    assert phone.post("/api/storage/clear", json={"what": "voices"}).status_code == 403, "this computer only"
    client.post("/api/storage/clear", json={"what": "voices"})
    assert not (config.TTS_DIR / "abc.mp3").exists()
    client.post("/api/storage/clear", json={"what": "translations"})
    assert services.translator.lookup("ar", "hello") is None
    assert services.translator.lookup("ar", "Hi") == "أهلًا", "the user's corrections are kept"
    assert client.post("/api/storage/clear", json={"what": "everything"}).status_code == 400
