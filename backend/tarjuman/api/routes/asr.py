"""Settings -> Transcription: the Whisper settings, this computer's hardware and the recommendation."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request

from ...asr_settings import MODELS, delete_model
from ..deps import body, fail, ok, services

router = APIRouter()


def _state(s, duration: float | None = None) -> dict:
    # aiReady: whether "fix the transcript with AI" can work (Settings -> AI is set up).
    return {**s.asr.public(duration), "status": s.whisper.status(), "aiReady": s.ai.ready}


@router.get("/api/asr")
async def asr_get(request: Request, duration: float = 0):
    """With ``duration`` (seconds), "effective" is what a recording that long would use."""
    return ok(**_state(services(request), duration or None))


@router.post("/api/asr")
async def asr_set(request: Request):
    s = services(request)
    s.asr.update(await body(request))
    return ok(**_state(s))


@router.post("/api/asr/delete")
async def asr_delete(request: Request):
    """{model}: deletes a downloaded model to free the disk. It is downloaded again if used later."""
    s = services(request)
    name = str((await body(request)).get("model") or "")
    if name not in MODELS:
        return fail("BAD_MODEL", status=400)
    if s.whisper.loading or not s.whisper.forget_model(name):
        return fail("ASR_BUSY", "Whisper يعمل الآن؛ احذف النموذج بعد انتهاء التفريغ", status=409)
    freed = await asyncio.to_thread(delete_model, name)
    return ok(freed=freed, **_state(s))


@router.post("/api/asr/prepare")
async def asr_prepare(request: Request):
    """Downloads and loads the chosen model now, so the first transcription doesn't wait for it."""
    s = services(request)
    started = s.whisper.prepare()
    return ok(started=started, **_state(s))
