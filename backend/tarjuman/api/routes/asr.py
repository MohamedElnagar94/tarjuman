"""Settings -> Transcription: the Whisper settings, this computer's hardware and the recommendation."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..deps import body, ok, services

router = APIRouter()


def _state(s, duration: float | None = None) -> dict:
    return {**s.asr.public(duration), "status": s.whisper.status()}


@router.get("/api/asr")
async def asr_get(request: Request, duration: float = 0):
    """With ``duration`` (seconds), "effective" is what a recording that long would use."""
    return ok(**_state(services(request), duration or None))


@router.post("/api/asr")
async def asr_set(request: Request):
    s = services(request)
    s.asr.update(await body(request))
    return ok(**_state(s))


@router.post("/api/asr/prepare")
async def asr_prepare(request: Request):
    """Downloads and loads the chosen model now, so the first transcription doesn't wait for it."""
    s = services(request)
    started = s.whisper.prepare()
    return ok(started=started, **_state(s))
