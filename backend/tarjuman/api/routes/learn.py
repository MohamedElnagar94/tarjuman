"""My words (vocabulary) and the pronunciation dictionary."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..deps import body, content_disposition, fail, ok, services

router = APIRouter()


@router.get("/api/vocab")
async def vocab(request: Request):
    return ok(items=services(request).vocab.items)


@router.post("/api/vocab")
async def vocab_add(request: Request):
    b = await body(request)
    if not str(b.get("word") or "").strip():
        return fail("NO_WORD", status=400)
    item, dup = services(request).vocab.add(b)
    return ok(item=item, duplicate=dup)


@router.post("/api/vocab/delete")
async def vocab_delete(request: Request):
    b = await body(request)
    services(request).vocab.delete(str(b.get("id") or ""))
    return ok()


@router.get("/api/vocab.csv")
async def vocab_csv(request: Request):
    return Response(
        ("﻿" + services(request).vocab.anki_csv()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": content_disposition("tarjuman-words.csv", True)},
    )


@router.get("/api/pronounce")
async def pronounce(request: Request):
    return ok(items=services(request).pronounce.items)


@router.post("/api/pronounce")
async def pronounce_set(request: Request):
    b = await body(request)
    return ok(items=services(request).pronounce.set(b.get("items")))


@router.post("/api/pronounce/preview")
async def pronounce_preview(request: Request):
    """The text as the voice will read it, after the dictionary."""
    b = await body(request)
    return ok(text=services(request).pronounce.apply(str(b.get("text") or "")))
