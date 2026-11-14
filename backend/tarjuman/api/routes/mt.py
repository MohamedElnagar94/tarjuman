"""Offline translation (translate/local.py): which language models are on this computer, downloading
and deleting them, and whether they come first ("offline") or only when Google refuses ("online")."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..deps import body, fail, ok, services

router = APIRouter()


@router.get("/api/mt")
async def mt_status(request: Request):
    return ok(**services(request).local_mt.status())


@router.post("/api/mt")
async def mt_settings(request: Request):
    b = await body(request)
    services(request).local_mt.set_prefer(str(b.get("prefer") or ""))
    return ok(**services(request).local_mt.status())


@router.post("/api/mt/install")
async def mt_install(request: Request):
    b = await body(request)
    pair = str(b.get("pair") or "")
    mt = services(request).local_mt
    if pair not in mt.status()["available"]:
        return fail("NOT_FOUND", status=404)
    mt.install(pair)
    return ok(**mt.status())


@router.post("/api/mt/delete")
async def mt_delete(request: Request):
    b = await body(request)
    mt = services(request).local_mt
    mt.delete(str(b.get("pair") or ""))
    return ok(**mt.status())
