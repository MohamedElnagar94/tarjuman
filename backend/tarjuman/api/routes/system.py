"""Health, live tab-audio translation, and the static files the clients load."""

from __future__ import annotations

import asyncio
import base64
import binascii

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response

from ... import APP_ID, __version__, config, storage
from ...asr import installed as whisper_installed
from ...core.deps import has
from ...core.net import lan_ip
from ...media import ffmpeg
from ..deps import body, fail, ok, services

router = APIRouter()


@router.get("/api/health")
async def health(request: Request):
    s = services(request)
    s.jobs.prune()
    python_ok = has("yt_dlp")
    return ok(
        app=APP_ID,
        version=__version__,
        port=request.app.state.port,
        cache=len(s.translator.cache),
        providers={**s.translator.stats, "googleCooling": s.translator.cooling},
        python=python_ok,
        ffmpeg=ffmpeg.available(),
        whisper=s.whisper.status(),
        tts=s.tts.status(),
        ai={"ready": s.ai.ready, "provider": s.ai.ai["provider"], "model": s.ai.model, "style": s.ai.ai["style"]},
        jobs=s.jobs.running_count(),
        paired=bool(getattr(request.state, "paired", True)),
        extensionAllowed=bool(getattr(request.state, "extension_allowed", True)),
    )


def _pair_links(request: Request) -> list[str]:
    code = request.app.state.pairing.code
    port = request.app.state.port
    ip = lan_ip()
    return [f"http://{ip}:{port}/pair?code={code}"] if ip else []


def _pairing_state(request: Request) -> dict:
    links = _pair_links(request)
    return {"links": links, "lan": bool(links), "devices": request.app.state.pairing.public()}


@router.get("/api/pairing")
async def pairing_info(request: Request):
    """For Settings → Phone: the link a phone opens once to be paired (the QR), and the paired devices."""
    return ok(**_pairing_state(request))


@router.post("/api/pairing/device")
async def pairing_device(request: Request):
    """{id, action: "remove"} unpairs one device; {id, action: "rename", name} renames it."""
    b = await body(request)
    p = request.app.state.pairing
    did = str(b.get("id") or "")
    if b.get("action") == "rename":
        p.rename(did, str(b.get("name") or ""))
    elif b.get("action") == "remove":
        p.remove(did)
    else:
        return fail("BAD_REQUEST", status=400)
    return ok(**_pairing_state(request))


@router.post("/api/pairing/unpair-all")
async def pairing_unpair_all(request: Request):
    request.app.state.pairing.remove_all()
    return ok(**_pairing_state(request))


@router.get("/api/storage")
async def storage_usage(request: Request):
    """How much each kind of data takes on disk."""
    return ok(usage=await asyncio.to_thread(storage.usage), voiceLimit=config.VOICE_CACHE_BYTES)


@router.post("/api/storage/clear")
async def storage_clear(request: Request):
    """{what: "voices" | "translations" | "tmp"}. Your corrections, files and videos are never touched."""
    b = await body(request)
    what = str(b.get("what") or "")
    if what not in ("voices", "translations", "tmp"):
        return fail("BAD_REQUEST", status=400)
    s = services(request)
    await asyncio.to_thread(storage.clear, s, what)
    if what == "translations":
        s.translator.flush()
    return ok(usage=await asyncio.to_thread(storage.usage))


@router.get("/api/extensions")
async def extensions(request: Request):
    t = request.app.state.extensions
    return ok(allowed=t.allowed, pending=t.pending)


@router.post("/api/extensions/set")
async def extensions_set(request: Request):
    """{id, allow: true|false}: allow a waiting extension, or remove one."""
    b = await body(request)
    t = request.app.state.extensions
    ext = str(b.get("id") or "")
    if ext:
        t.allow(ext) if b.get("allow") else t.remove(ext)
    return ok(allowed=t.allowed, pending=t.pending)


@router.post("/api/pairing/reset")
async def pairing_reset(request: Request):
    """A new invite code: the old QR stops pairing new devices. Paired devices stay paired."""
    request.app.state.pairing.new_code()
    return ok(**_pairing_state(request))


@router.post("/api/live")
async def live(request: Request):
    """A few seconds of tab audio from the extension: transcribe, translate, and optionally speak."""
    b = await body(request)
    s = services(request)
    tl = b.get("tl") or "ar"
    if not b.get("audio_b64"):
        return fail("NO_AUDIO", status=400)
    if not whisper_installed():
        return fail("WHISPER_NOT_INSTALLED")
    try:
        pcm = base64.b64decode(b["audio_b64"])
    except (binascii.Error, ValueError):
        return fail("NO_AUDIO", status=400)
    try:
        r = await s.whisper.transcribe_pcm(pcm)
    except Exception as e:  # noqa: BLE001
        return fail(getattr(e, "code", "ASR_ERROR"), str(e)[:300])
    text = " ".join(str(r["text"] or "").split())
    ar = ""
    if text:
        ar = (await s.translator.translate_many([text], sl=r["lang"] or "auto", tl=tl)).get(text, "")
    audio_b64 = audio_mime = ""
    if b.get("tts") and ar:
        try:
            t = await s.tts.speak(ar, tl, b.get("voice") or "")
            audio_b64, audio_mime = base64.b64encode(t.buf).decode("ascii"), t.mime
        except Exception:  # noqa: BLE001 — the extension falls back to the browser's voice
            pass
    return ok(text=text, ar=ar, lang=r["lang"], audio_b64=audio_b64, audio_mime=audio_mime)


@router.get("/dub-engine.js")
async def dub_engine():
    return FileResponse(config.DUB_ENGINE_JS, media_type="text/javascript; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


@router.get("/favicon.svg")
async def favicon():
    if not config.ICON_SVG.exists():
        return Response(status_code=404)
    return FileResponse(config.ICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
