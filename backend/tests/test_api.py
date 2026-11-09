"""The HTTP API, offline: translation and voices are replaced by fakes."""

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
def client(services):
    with TestClient(create_app(services, warm=False), headers=LOCAL) as c:
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


def test_settings_answer_only_to_this_computer(client):
    # TestClient's peer address is "testclient", which is not loopback.
    r = client.get("/api/settings")
    assert r.status_code == 403 and r.json()["code"] == "LOCAL_ONLY"


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
