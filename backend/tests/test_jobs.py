import asyncio
import os

import pytest

from tarjuman import config
from tarjuman.core.errors import AppError
from tarjuman.jobs.manager import JobManager


async def test_heavy_jobs_of_one_kind_take_turns_and_a_queued_job_can_be_cancelled():
    jm = JobManager()
    running = []
    release = asyncio.Event()

    async def work(job):
        running.append(job.id)
        await release.wait()

    a, b, c = jm.new("dub", "v1"), jm.new("dub", "v2"), jm.new("dub", "v3")
    for j in (a, b, c):
        jm.start(j, work)
    await asyncio.sleep(0.05)
    assert running == [a.id], "one dub at a time"
    assert b.status == "queued" and c.status == "queued"
    jm.cancel(c)
    release.set()
    await asyncio.sleep(0.05)
    assert running == [a.id, b.id], "the next one starts; the cancelled one never runs"
    assert a.status == "done" and c.status == "cancelled"


async def test_different_kinds_run_side_by_side():
    jm = JobManager()
    started = []

    async def work(job):
        started.append(job.type)
        await asyncio.sleep(0.05)

    jm.start(jm.new("dub", "v1"), work)
    jm.start(jm.new("fetch", "f1"), work)
    jm.start(jm.new("fetch", "f2"), work)
    await asyncio.sleep(0.02)
    assert sorted(started) == ["dub", "fetch", "fetch"]


async def test_heavy_jobs_of_different_kinds_share_a_limit(monkeypatch):
    monkeypatch.setattr(config, "HEAVY_JOBS", 2)
    jm = JobManager()
    running, peak = set(), 0
    release = asyncio.Event()

    async def work(job):
        nonlocal peak
        running.add(job.type)
        peak = max(peak, len(running))
        await release.wait()
        running.discard(job.type)

    w, d, v = jm.new("whisper", "a"), jm.new("dub", "b"), jm.new("subvideo", "c")
    f = jm.new("fetch", "f")
    for j in (w, d, v, f):
        jm.start(j, work)
    await asyncio.sleep(0.05)
    assert running == {"whisper", "dub", "fetch"}, "two heavy jobs, and the download isn't held back"
    assert v.status == "queued"
    jm.cancel(v)
    release.set()
    await asyncio.sleep(0.05)
    assert peak == 3 and v.status == "cancelled" and w.status == d.status == "done"


async def test_one_heavy_place_makes_them_take_turns(monkeypatch):
    monkeypatch.setattr(config, "HEAVY_JOBS", 1)
    jm = JobManager()
    order, together = [], 0
    busy = 0

    async def work(job):
        nonlocal busy, together
        busy += 1
        together = max(together, busy)
        order.append(job.type)
        await asyncio.sleep(0.02)
        busy -= 1

    for kind in ("whisper", "dub", "subvideo"):
        jm.start(jm.new(kind, kind), work)
    await asyncio.sleep(0.2)
    assert together == 1 and sorted(order) == ["dub", "subvideo", "whisper"]


async def test_a_batch_waiting_on_its_video_cannot_block_itself(monkeypatch):
    monkeypatch.setattr(config, "HEAVY_JOBS", 1)
    jm = JobManager()
    done = []

    async def batch(job):
        for n in range(2):  # like run_batch: the batch holds its own turn and takes the video's
            sub = jm.child("dub", f"v{n}")
            async with jm.slot(sub.type):
                await asyncio.sleep(0.01)
                done.append(sub.videoId)

    jm.start(jm.new("batch", "batch"), batch)
    await asyncio.wait_for(_until(lambda: len(done) == 2), 2)


async def _until(cond):
    while not cond():
        await asyncio.sleep(0.01)


async def test_the_waiting_queue_has_a_limit(monkeypatch):
    monkeypatch.setattr(config, "MAX_QUEUE", 3)
    jm = JobManager()
    release = asyncio.Event()

    async def work(_job):
        await release.wait()

    jm.start(jm.new("dub", "running"), work)
    await asyncio.sleep(0.02)
    for n in range(3):
        jm.start(jm.new("dub", f"q{n}"), work)
    with pytest.raises(AppError) as e:
        jm.new("dub", "one-too-many")
    assert e.value.code == "QUEUE_FULL"
    assert jm.child("dub", "a-batch-video"), "a playlist's own videos are not refused"
    jm.cancel_all()
    release.set()


def test_env_file_fills_in_only_what_is_not_already_set(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text(
        "# a comment\n\nTARJUMAN_TEST_A=1\nTARJUMAN_TEST_B = two words \nTARJUMAN_TEST_C=\"quoted # kept\"\n"
        "TARJUMAN_TEST_D=5 # trailing comment\nexport TARJUMAN_TEST_E=e\nTARJUMAN_TEST_SET=from-file\nnot a setting\n",
        encoding="utf-8",
    )
    for k in "ABCDE":
        monkeypatch.delenv("TARJUMAN_TEST_" + k, raising=False)
    monkeypatch.setenv("TARJUMAN_TEST_SET", "from-real-environment")
    applied = config.load_env_file(f)
    try:
        assert applied == {
            "TARJUMAN_TEST_A": "1", "TARJUMAN_TEST_B": "two words", "TARJUMAN_TEST_C": "quoted # kept",
            "TARJUMAN_TEST_D": "5", "TARJUMAN_TEST_E": "e",
        }
        assert os.environ["TARJUMAN_TEST_SET"] == "from-real-environment", "the real environment wins"
    finally:
        for k in applied:
            os.environ.pop(k, None)
    assert config.load_env_file(tmp_path / "missing.env") == {}


def test_a_setting_that_is_not_a_number_falls_back(monkeypatch):
    monkeypatch.setenv("TARJUMAN_TEST_N", "lots")
    assert config._number("TARJUMAN_TEST_N", 7) == 7
    monkeypatch.setenv("TARJUMAN_TEST_N", "2.5")
    assert config._number("TARJUMAN_TEST_N", 7) == 2.5
