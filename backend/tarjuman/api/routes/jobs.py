"""Jobs (Whisper, dubbed and subtitled MP4, playlists) and the finished-files library."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from ... import config
from ...core.net import ensure_public_url
from ...jobs import runners
from ..deps import body, content_disposition, fail, ok, services

router = APIRouter()

LIB_DIRS = {"dubbed": config.DUBBED, "subs": config.OUTPUT}
LIB_TYPES = {
    ".mp4": "video/mp4",
    ".m4a": "audio/mp4",
    ".srt": "application/x-subrip; charset=utf-8",
    ".vtt": "text/vtt; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def send_file(path: Path, name: str, mime: str, download: bool) -> FileResponse:
    # FileResponse answers Range requests, so the player can seek in previews.
    return FileResponse(
        path, media_type=mime,
        headers={"Content-Disposition": content_disposition(name, download), "Cache-Control": "no-store"},
    )


@router.post("/api/whisper/job")
async def whisper_start(request: Request):
    b = await body(request)
    return ok(id=runners.start_whisper(services(request), b.get("url") or "", b.get("tl") or "ar"))


@router.get("/api/whisper/job")
async def whisper_job(request: Request, id: str = ""):
    j = services(request).jobs.get(id)
    if not j:
        return fail("NO_JOB", status=404)
    d = j.public()
    d.update(srcLang=j.extra.get("srcLang", ""), tl=j.opts.get("tl"))
    if j.status == "done":
        d["cues"] = j.extra.get("cues", [])
    return d


@router.get("/api/whisper/status")
async def whisper_status(request: Request):
    return ok(**services(request).whisper.status())


@router.post("/api/dub")
@router.post("/api/dub/job")
async def dub_start(request: Request):
    b = await body(request)
    return ok(id=runners.start_dub(services(request), b.get("url") or "", b))


@router.get("/api/dub/job")
@router.get("/api/dub")
async def dub_job(request: Request, id: str = ""):
    j = services(request).jobs.get(id)
    return j.public() if j else fail("NO_JOB", status=404)


@router.get("/api/dub/file")
async def dub_file(request: Request, id: str = "", dl: str = "0"):
    j = services(request).jobs.get(id)
    if not j or j.status != "done" or not j.mp4 or not j.mp4.exists():
        return fail("NO_FILE", status=404)
    mime = "audio/mp4" if j.mp4.suffix.lower() == ".m4a" else "video/mp4"
    return send_file(j.mp4, j.fileName or "dubbed" + j.mp4.suffix, mime, dl == "1")


@router.post("/api/subvideo")
async def subvideo(request: Request):
    b = await body(request)
    return ok(id=runners.start_subvideo(services(request), b.get("url") or "", b))


@router.post("/api/batch")
async def batch(request: Request):
    b = await body(request)
    link = str(b.get("url") or "").strip()
    if not re.match(r"^https?://", link, re.I):
        return fail("BAD_URL")
    await ensure_public_url(link)
    return ok(id=runners.start_batch(services(request), link, b))


@router.post("/api/job/cancel")
async def cancel(request: Request):
    b = await body(request)
    s = services(request)
    j = s.jobs.get(str(b.get("id") or ""))
    if not j:
        return fail("NO_JOB", status=404)
    return {"ok": s.jobs.cancel(j)}


@router.get("/api/jobs")
async def jobs(request: Request):
    s = services(request)
    s.jobs.prune()
    return ok(jobs=s.jobs.public())


def library_path(kind: str, name: str) -> Path | None:
    folder = LIB_DIRS.get(kind)
    if not folder or not name or Path(name).name != name:
        return None
    p = folder / name
    return p if p.suffix.lower() in LIB_TYPES and p.is_file() else None


@router.get("/api/library")
async def library():
    items = []
    for kind, folder in LIB_DIRS.items():
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for f in entries:
            if f.suffix.lower() in LIB_TYPES and f.is_file():
                st = f.stat()
                items.append({"kind": kind, "name": f.name, "size": st.st_size, "mtime": int(st.st_mtime * 1000)})
    return ok(items=sorted(items, key=lambda x: -x["mtime"]))


@router.get("/api/library/file")
async def library_file(kind: str = "", name: str = "", dl: str = "0"):
    p = library_path(kind, name)
    if not p:
        return fail("NO_FILE", status=404)
    return send_file(p, name, LIB_TYPES[p.suffix.lower()], dl == "1")


@router.post("/api/library/delete")
async def library_delete(request: Request):
    b = await body(request)
    p = library_path(str(b.get("kind") or ""), str(b.get("name") or ""))
    if not p:
        return fail("NO_FILE", status=404)
    p.unlink(missing_ok=True)
    return ok()
