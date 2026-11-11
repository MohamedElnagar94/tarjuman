"""Background jobs (Whisper, dubbing, subtitled video, playlists, downloads) with progress and cancel.

A job runs as an asyncio task. Subprocesses it starts are tracked so cancelling kills them, and
in-process work (Whisper) checks ``job.cancelled`` between steps."""

from __future__ import annotations

import asyncio
import os
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from .. import config
from ..core.errors import AppError, Cancelled


@dataclass
class Job:
    id: str
    type: str
    videoId: str
    status: str = "queued"
    phase: str = "في الانتظار"
    progress: int = 0
    message: str = ""
    title: str = ""
    startedAt: int = field(default_factory=lambda: int(time.time() * 1000))
    size: int = 0
    fileName: str = ""
    mp4: Path | None = None
    dubInfo: dict | None = None
    cancelled: bool = False
    opts: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)  # per-type results (cues, media, items…)
    current: "Job | None" = None  # a batch's running child job
    procs: set = field(default_factory=set, repr=False)

    @property
    def active(self) -> bool:
        return self.status in ("queued", "running")

    def check(self) -> None:
        if self.cancelled:
            raise Cancelled()

    def public(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ok": True,
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "phase": self.phase,
            "progress": self.progress,
            "message": self.message,
            "title": self.title,
            "videoId": self.videoId,
            "startedAt": self.startedAt,
            "size": self.size,
            "fileName": self.fileName,
            "dubInfo": self.dubInfo,
            "fileUrl": f"/api/dub/file?id={self.id}" if self.mp4 and self.status == "done" else "",
        }
        if self.type == "batch":
            d["what"] = self.opts.get("what")
            d["items"] = [
                {"id": x["id"], "title": x["title"], "status": x["status"], "message": x.get("message", "")}
                for x in self.extra.get("items", [])
            ]
        return d


# How many jobs of each kind run at once; the rest wait their turn ("queued"). Dubbing, burning
# subtitles and Whisper each keep the CPU busy; running several together only makes all of them slow
# and can run the computer out of memory.
LIMITS = {"whisper": 1, "dub": 1, "subvideo": 1, "batch": 1, "fetch": 2}
QUEUED_PHASE = "في انتظار انتهاء مهمة أخرى"


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self._slots: dict[str, asyncio.Semaphore] = {}

    def slot(self, type_: str) -> asyncio.Semaphore:
        """The turn for one kind of job. A playlist batch takes it for each video it dubs or subtitles."""
        if type_ not in self._slots:
            self._slots[type_] = asyncio.Semaphore(LIMITS.get(type_, 2))
        return self._slots[type_]

    def new(self, type_: str, video_id: str, **opts: Any) -> Job:
        jid = type_[0] + format(int(time.time() * 1000), "x") + secrets.token_hex(2)
        job = Job(id=jid, type=type_, videoId=video_id, opts=opts)
        self.jobs[jid] = job
        return job

    def get(self, jid: str) -> Job | None:
        return self.jobs.get(jid)

    def find_active(self, type_: str, video_id: str) -> Job | None:
        return next((j for j in self.jobs.values() if j.type == type_ and j.videoId == video_id and j.active), None)

    def running_count(self) -> int:
        return sum(1 for j in self.jobs.values() if j.active)

    def prune(self) -> None:
        cutoff = (time.time() - 6 * 3600) * 1000
        for jid in [k for k, j in self.jobs.items() if not j.active and j.startedAt < cutoff]:
            del self.jobs[jid]

    def public(self) -> list[dict]:
        return [j.public() for j in reversed(list(self.jobs.values()))]

    def start(self, job: Job, fn: Callable[[Job], Awaitable[None]]) -> None:
        job.status = "queued"
        job.phase = QUEUED_PHASE

        async def runner() -> None:
            try:
                async with self.slot(job.type):
                    if job.cancelled:
                        return
                    job.status = "running"
                    await fn(job)
                if job.status == "running":
                    job.status = "done"
            except BaseException as e:  # noqa: BLE001
                if job.cancelled:
                    return
                job.status = "error"
                job.message = str(getattr(e, "message", None) or e)[:400]
            finally:
                job.procs.clear()

        asyncio.ensure_future(runner())

    def cancel(self, job: Job) -> bool:
        if not job.active:
            return False
        if job.current:
            self.cancel(job.current)
        job.cancelled = True
        for p in list(job.procs):
            try:
                p.kill()
            except ProcessLookupError:
                pass
        job.status = "cancelled"
        job.phase = "أُلغيت"
        return True

    def cancel_all(self) -> None:
        for j in list(self.jobs.values()):
            self.cancel(j)


class ProcError(AppError):
    def __init__(self, code: int, stderr: str):
        super().__init__("PROC_FAILED", f"exit {code}")
        self.stderr = stderr


# A long ffmpeg or yt-dlp run can print for hours. What is kept of it is bounded: the end of stderr
# (where the reason for a failure is) and far more stdout than any real answer needs.
STDOUT_KEEP = 32 << 20
STDERR_KEEP = 256 << 10


class _Tail:
    """The last ``limit`` characters of a stream of lines."""

    def __init__(self, limit: int):
        self.limit = limit
        self.lines: deque[str] = deque()
        self.size = 0

    def add(self, line: str) -> None:
        self.lines.append(line)
        self.size += len(line)
        while self.size > self.limit and len(self.lines) > 1:
            self.size -= len(self.lines.popleft())

    def text(self) -> str:
        return "".join(self.lines)


async def run_proc(
    job: Job,
    cmd: list[str],
    *,
    cwd: Path | None = None,
    on_line: Callable[[str], None] | None = None,
) -> str:
    """Run a subprocess that belongs to ``job`` (cancel kills it). Returns stdout. ``on_line`` sees
    every stdout and stderr line as it arrives (progress)."""
    job.check()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
        env=config.child_env(),
        creationflags=0x08000000 if os.name == "nt" else 0,  # CREATE_NO_WINDOW
    )
    job.procs.add(proc)
    out = _Tail(STDOUT_KEEP)
    err = _Tail(STDERR_KEEP)

    async def pump(stream, sink: _Tail) -> None:
        async for raw in stream:
            line = raw.decode("utf-8", "replace")
            sink.add(line)
            if on_line:
                on_line(line)

    try:
        await asyncio.gather(pump(proc.stdout, out), pump(proc.stderr, err))
        code = await proc.wait()
    finally:
        job.procs.discard(proc)
    if job.cancelled:
        raise Cancelled()
    if code != 0:
        raise ProcError(code, err.text()[-4000:])
    return out.text()
