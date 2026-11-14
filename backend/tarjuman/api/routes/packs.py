"""Voice packs (engines/packs.py): the original speaker's voice (XTTS) and Arabic dialect voices (Habibi),
installed on request because they need PyTorch. This computer only."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request

from ...asr_settings import hardware
from ..deps import body, fail, ok, services

router = APIRouter()


@router.get("/api/packs")
async def packs_status(request: Request):
    hw = await asyncio.to_thread(hardware)
    return ok(**services(request).packs.status(hw))


@router.post("/api/packs/install")
async def packs_install(request: Request):
    b = await body(request)
    s = services(request)
    try:
        pack = s.packs.get(str(b.get("name") or ""))
    except Exception:  # noqa: BLE001
        return fail("NOT_FOUND", status=404)
    if pack.spec["licence"] == "CPML":
        if not b.get("accept"):
            return fail("LICENCE_NOT_ACCEPTED", "وافق على رخصة Coqui غير التجارية أولًا", status=400)
        pack.accept()
    hw = await asyncio.to_thread(hardware)
    gpu = bool(hw.get("cuda")) and not hw.get("gpuOld")
    asyncio.ensure_future(pack.install(gpu))
    await asyncio.sleep(0.05)
    return ok(**s.packs.status(hw))


@router.post("/api/packs/delete")
async def packs_delete(request: Request):
    b = await body(request)
    s = services(request)
    try:
        s.packs.get(str(b.get("name") or "")).delete()
    except Exception:  # noqa: BLE001
        return fail("NOT_FOUND", status=404)
    return ok(**s.packs.status(await asyncio.to_thread(hardware)))
