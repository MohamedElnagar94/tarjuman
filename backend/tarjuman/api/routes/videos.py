"""Cues, translation, subtitle files, voices, speech and live dub plans."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ... import config
from ...captions.formats import SUB_FORMATS
from ...captions.models import Cue
from ...core.errors import AppError
from ...core.text import norm_lang, safe_name
from ...voice.gate import PLAY
from ..deps import body, content_disposition, fail, ok, qnum, services

router = APIRouter()


@router.get("/api/cues")
async def cues(request: Request, url: str = "", tl: str = "ar", fresh: str = "0"):
    data = await services(request).captions.get(url, tl, fresh=fresh == "1")
    return ok(**data.to_dict())


@router.post("/api/translate")
async def translate(request: Request):
    b = await body(request)
    texts = [t for t in (b.get("texts") or [])[:200] if isinstance(t, str)]
    found = await services(request).translator.translate_many(texts, sl=b.get("sl") or "auto", tl=b.get("tl") or "ar")
    return ok(map=found)


@router.post("/api/translate/edit")
async def translate_edit(request: Request):
    b = await body(request)
    src = str(b.get("src") or "").strip()
    if not src:
        return fail("NO_TEXT", status=400)
    services(request).translator.set_edit(b.get("tl") or "ar", src, str(b.get("ar") or "").strip())
    return ok()


@router.get("/api/subs")
@router.get("/api/srt")
async def subs(request: Request, url: str = "", tl: str = "ar", mode: str = "ar", format: str = "srt", save: str = "0"):
    s = services(request)
    fmt = format if format in SUB_FORMATS else "srt"
    data = await s.captions.get(url, tl)
    if not data.alreadyTranslated:
        await s.translator.translate_cues(data.cues, tl=tl, sl=data.srcLang or "auto")
    fn, mime = SUB_FORMATS[fmt]
    suffix = "bilingual" if mode == "bi" else (data.srcLang or "src") if mode == "src" else norm_lang(tl)
    filename = f"{safe_name(data.title)}.{suffix}.{fmt}"
    text = fn(data.cues, mode)
    bom = "" if fmt == "vtt" else "﻿"
    if save == "1":
        (config.OUTPUT / filename).write_text("﻿" + text, encoding="utf-8")
    return Response(
        (bom + text).encode("utf-8"),
        media_type=f"{mime}; charset=utf-8",
        headers={"Content-Disposition": content_disposition(filename, True)},
    )


@router.get("/api/voices")
async def voices(request: Request, lang: str = "ar"):
    return ok(voices=services(request).tts.voices(lang))


@router.get("/api/tts")
async def tts(request: Request, text: str = "", lang: str = "ar", voice: str = "", rate: str = "0"):
    text = text[:1500]
    if not text.strip():
        return fail("NO_TEXT", status=400)
    try:
        r = await services(request).tts.speak(text, lang, voice, qnum(rate, 0), priority=PLAY)
    except Exception as e:  # noqa: BLE001
        return fail("TTS_ERROR", str(e)[:200])
    return Response(
        r.buf,
        media_type=r.mime,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Audio-Duration": str(r.duration or 0),
            "X-TTS-Engine": r.engine,
            "Access-Control-Expose-Headers": "X-Audio-Duration, X-TTS-Engine",
        },
    )


def _plan_reply(plan, start: float, end: float, blocks: list[dict]) -> JSONResponse:
    last = plan.blocks[-1] if plan.blocks else None
    return ok(**{"from": start, "to": end, "total": len(plan.blocks), "end": last.end if last else 0, "blocks": blocks})


@router.get("/api/dubplan")
async def dubplan(
    request: Request, url: str = "", tl: str = "ar", voice: str = "", urgent: str = "0",
):
    """The dub plan for part of the video; the player asks for the next part while it plays."""
    q = request.query_params
    start = max(0.0, qnum(q.get("from"), 0))
    end = qnum(q.get("to"), 0) or start + 120
    s = services(request)
    plan = await s.live.plan_for(url, tl)
    blocks = await s.live.blocks(
        plan, start, end, voice, tl, measure=True, urgent=urgent == "1", speed=qnum(q.get("speed"), 1.0)
    )
    return _plan_reply(plan, start, end, blocks)


@router.post("/api/dubplan/cues")
async def dubplan_cues(request: Request):
    """The same plan for captions the extension took from another site's player (Coursera, Udemy…)."""
    b = await body(request)
    tl = b.get("tl") or "ar"
    start = max(0.0, qnum(b.get("from"), 0))
    end = qnum(b.get("to"), 0) or start + 120
    cues = []
    for c in (b.get("cues") or [])[:20000]:
        if not isinstance(c, dict):
            continue
        cue = Cue(qnum(c.get("start"), 0), qnum(c.get("end"), 0), str(c.get("src") or "")[:600])
        if cue.src.strip() and cue.end > cue.start:
            cues.append(cue)
    if not cues:
        raise AppError("NO_CUES")
    s = services(request)
    plan = s.live.plan_for_cues(cues, b.get("sl") or "auto", tl)
    blocks = await s.live.blocks(
        plan, start, end, b.get("voice") or "", tl, measure=True, urgent=bool(b.get("urgent")), speed=qnum(b.get("speed"), 1.0)
    )
    return _plan_reply(plan, start, end, blocks)
