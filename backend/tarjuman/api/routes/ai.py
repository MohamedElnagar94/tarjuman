"""AI settings (this computer only), the script writer test, summary and questions."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from ...core.errors import AppError
from ..deps import body, ok, services

router = APIRouter()


@router.get("/api/settings")
async def settings(request: Request):
    return ok(**services(request).ai.public())


@router.post("/api/settings")
async def settings_set(request: Request):
    b = await body(request)
    s = services(request)
    if isinstance(b.get("ai"), dict):
        s.ai.update(b["ai"])
    return ok(**s.ai.public())


@router.post("/api/ai/test")
async def ai_test(request: Request):
    """A quick check of the settings: one sentence."""
    s = services(request)
    if not s.ai.ready:
        raise AppError("AI_NOT_READY", "فعّل الخاصية وأدخل المفتاح أولًا")
    t0 = time.time()
    text = await s.writer.test()
    return ok(text=text, ms=round((time.time() - t0) * 1000), model=s.ai.model)


@router.post("/api/ai/summary")
async def ai_summary(request: Request):
    b = await body(request)
    s = services(request)
    tl = b.get("tl") or "ar"
    data = await s.captions.get(b.get("url") or "", tl)
    return ok(**(await s.insights.summary(data, tl)))


@router.post("/api/ai/ask")
async def ai_ask(request: Request):
    b = await body(request)
    s = services(request)
    tl = b.get("tl") or "ar"
    data = await s.captions.get(b.get("url") or "", tl)
    return ok(**(await s.insights.ask(data, tl, b.get("question") or "")))
