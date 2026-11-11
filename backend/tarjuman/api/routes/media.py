"""Videos from your computer (uploads) or any site (yt-dlp downloads)."""

from __future__ import annotations

import logging
import shutil

from fastapi import APIRouter, Request

from ... import config
from ...core.errors import AppError
from ...jobs import runners
from ..deps import body, fail, ok, services
from .jobs import send_file

router = APIRouter()


log = logging.getLogger("tarjuman.media")
DISK_CHECK_EVERY = 64 << 20


def _free_bytes(folder) -> int:
    """Free space on the disk. When it can't be measured the answer is 0: an upload is refused
    rather than accepted blindly."""
    try:
        return shutil.disk_usage(folder).free
    except OSError as e:
        log.warning("cannot measure free disk space: %s", e)
        return 0


@router.post("/api/media/upload")
async def upload(request: Request, name: str = "video"):
    """The file is written to disk as it arrives, never held in memory whole. Uploads are capped
    (TARJUMAN_MAX_UPLOAD_GB) and stop before they would leave the disk nearly full."""
    s = services(request)
    limit = config.MAX_UPLOAD_BYTES
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        declared = 0
    if declared > limit:
        return fail("UPLOAD_TOO_LARGE", f"أقصى حجم للرفع {limit // (1 << 30)} غيغابايت", status=413)
    # Without a declared size the reserve alone must be free; the loop below keeps checking.
    if declared > _free_bytes(s.media.folder) - config.DISK_RESERVE_BYTES:
        return fail("DISK_FULL", "لا توجد مساحة كافية على القرص لهذا الملف", status=507)
    item = s.media.upload_target(name)
    size = 0
    next_check = DISK_CHECK_EVERY
    try:
        item.path.parent.mkdir(parents=True, exist_ok=True)
        with open(item.path, "wb") as fh:
            async for chunk in request.stream():
                size += len(chunk)
                if size > limit:
                    raise AppError("UPLOAD_TOO_LARGE", f"أقصى حجم للرفع {limit // (1 << 30)} غيغابايت")
                if size >= next_check:
                    next_check = size + DISK_CHECK_EVERY
                    if _free_bytes(s.media.folder) < config.DISK_RESERVE_BYTES:
                        raise AppError("DISK_FULL", "امتلأ القرص أثناء الرفع")
                fh.write(chunk)
    except AppError as e:
        s.media.discard(item)
        return fail(e.code, e.message, status=413 if e.code == "UPLOAD_TOO_LARGE" else 507)
    except BaseException:
        s.media.discard(item)
        raise
    if not size:
        s.media.discard(item)
        return fail("EMPTY_FILE", status=400)
    item.size = size
    s.media.save()
    return ok(**item.public())


@router.post("/api/media/fetch")
async def fetch(request: Request):
    b = await body(request)
    return ok(id=runners.start_fetch(services(request), str(b.get("url") or "").strip()))


@router.get("/api/media/job")
async def media_job(request: Request, id: str = ""):
    j = services(request).jobs.get(id)
    if not j:
        return fail("NO_JOB", status=404)
    return {**j.public(), "media": j.extra.get("media")}


@router.get("/api/media")
async def media_list(request: Request):
    return ok(items=services(request).media.list())


@router.get("/api/media/info")
async def media_info(request: Request, id: str = ""):
    m = services(request).media.get(id)
    return ok(**m.public()) if m else fail("NO_MEDIA", status=404)


@router.get("/api/media/file")
async def media_file(request: Request, id: str = ""):
    m = services(request).media.get(id)
    if not m or not m.path.exists():
        return fail("NO_MEDIA", status=404)
    return send_file(m.path, m.title + m.path.suffix, m.mime(), False)


@router.post("/api/media/delete")
async def media_delete(request: Request):
    b = await body(request)
    return ok() if services(request).media.delete(str(b.get("id") or "")) else fail("NO_MEDIA", status=404)
