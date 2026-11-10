import asyncio

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
