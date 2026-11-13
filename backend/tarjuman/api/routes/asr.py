"""Settings -> Transcription: the Whisper settings, this computer's hardware and the recommendation."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request

from ...asr_custom import inspect
from ...asr_settings import CUSTOM, MODELS, delete_model
from ...core.errors import AppError
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
    if name not in MODELS and name not in CUSTOM:
        return fail("BAD_MODEL", status=400)
    if s.whisper.loading or not s.whisper.forget_model(name):
        return fail("ASR_BUSY", "Whisper يعمل الآن؛ احذف النموذج بعد انتهاء التفريغ", status=409)
    freed = await asyncio.to_thread(delete_model, name)
    return ok(freed=freed, **_state(s))


@router.post("/api/asr/custom/check")
async def asr_custom_check(request: Request):
    """{source}: looks at a model (a Hugging Face repository or a folder) before it is added."""
    try:
        info = await inspect(str((await body(request)).get("source") or ""))
    except AppError as e:
        return fail(e.code, e.message, status=400)
    return ok(model=info)


@router.post("/api/asr/custom/add")
async def asr_custom_add(request: Request):
    """{source}: adds the model and chooses it. It is downloaded on the first transcription, or with
    "prepare now"."""
    s = services(request)
    try:
        info = await inspect(str((await body(request)).get("source") or ""))
    except AppError as e:
        return fail(e.code, e.message, status=400)
    s.asr.add_custom(info)
    return ok(**_state(s))


@router.post("/api/asr/custom/remove")
async def asr_custom_remove(request: Request):
    """{id}: takes the model off the list; a downloaded repository is deleted from the disk too (a
    folder of the user's is left where it is)."""
    s = services(request)
    model_id = str((await body(request)).get("id") or "")
    if model_id not in CUSTOM:
        return fail("BAD_MODEL", status=400)
    if s.whisper.loading or not s.whisper.forget_model(model_id):
        return fail("ASR_BUSY", "Whisper يعمل الآن؛ احذف النموذج بعد انتهاء التفريغ", status=409)
    freed = await asyncio.to_thread(delete_model, model_id)
    s.asr.remove_custom(model_id)
    return ok(freed=freed, **_state(s))


@router.post("/api/asr/prepare")
async def asr_prepare(request: Request):
    """Downloads and loads the chosen model now, so the first transcription doesn't wait for it."""
    s = services(request)
    started = s.whisper.prepare()
    return ok(started=started, **_state(s))
