"""Failures that must stay contained: cut translations and subprocesses that never stop printing."""

import sys
from urllib.parse import parse_qs, urlparse

from tarjuman.jobs.manager import JobManager, _Tail, run_proc
from tarjuman.translate import providers
from tarjuman.translate.providers import MyMemory, split_bytes


def test_split_bytes_keeps_every_word_and_respects_the_limit():
    arabic = "هذه جملة عربية طويلة تتكرر كثيرًا. " * 40
    mixed = "The model يسمى large language model and it works well! " * 30
    for text in (arabic, mixed, "word " * 300):
        pieces = split_bytes(text, 480)
        assert len(pieces) > 1
        assert all(len(p.encode()) <= 480 for p in pieces)
        assert " ".join(pieces).split() == text.split(), "no word lost or cut"
    assert split_bytes("short", 480) == ["short"]
    long_word = "ب" * 600  # 1200 bytes, no place to cut: cut between characters, never inside one
    assert "".join(split_bytes(long_word, 480)) == long_word


async def test_mymemory_translates_a_long_text_in_pieces(monkeypatch):
    asked = []

    async def fake_get_json(url, **_):
        q = parse_qs(urlparse(url).query)["q"][0]
        asked.append(q)
        return {"responseData": {"translatedText": f"<{len(asked)}>"}}

    async def no_sleep(_s):
        pass

    monkeypatch.setattr(providers.http, "get_json", fake_get_json)
    monkeypatch.setattr(providers.asyncio, "sleep", no_sleep)
    text = "هذه جملة عربية طويلة تتكرر كثيرًا. " * 40
    out = await MyMemory().translate(text, "ar", "en")
    assert len(asked) > 1 and all(len(q.encode()) <= 480 for q in asked)
    assert " ".join(asked).split() == text.split(), "the whole text was sent"
    assert out == " ".join(f"<{i}>" for i in range(1, len(asked) + 1))


def test_tail_keeps_only_the_end():
    t = _Tail(100)
    for i in range(1000):
        t.add(f"line {i}\n")
    assert len(t.text()) <= 100 and t.text().endswith("line 999\n")


async def test_run_proc_survives_a_very_talkative_process(monkeypatch):
    from tarjuman.jobs import manager

    monkeypatch.setattr(manager, "STDOUT_KEEP", 2000)
    monkeypatch.setattr(manager, "STDERR_KEEP", 2000)
    job = JobManager().new("fetch", "x")
    seen = 0

    def on_line(_line):
        nonlocal seen
        seen += 1

    code = "import sys\nfor i in range(20000):\n    print('out', i)\n    print('err', i, file=sys.stderr)\nprint('LAST')"
    out = await run_proc(job, [sys.executable, "-c", code], on_line=on_line)
    assert seen == 40001, "progress still sees every line"
    assert len(out) <= 2000 and out.strip().endswith("LAST")
