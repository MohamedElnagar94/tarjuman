"""Health, live tab-audio translation, and the static files the clients load."""

from __future__ import annotations

import asyncio
import base64
import binascii
import re
import threading
import webbrowser

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response

from ... import APP_ID, __version__, config, desktop_settings, storage, updates
from ...asr import installed as whisper_installed
from ...core.deps import has
from ...core.net import lan_ip
from ...media import ffmpeg
from ..deps import body, fail, ok, services

# The protocol version in /api/health (see docs/specs.md).
API_VERSION = 1

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
        # The protocol the web app and the extension speak with this server. Raised only when a
        # change would break an older client; a client that knows a lower number asks to update.
        api=API_VERSION,
    )


def _desktop_state(request: Request) -> dict:
    return {
        "available": request.app.state.desktop is not None,
        "supported": desktop_settings.supported(),
        "settings": request.app.state.desktop_settings.public(),
    }


@router.get("/api/desktop")
async def desktop_get(request: Request):
    """The four desktop settings (Settings → Desktop). "available" says whether this server runs inside
    the desktop app, where they take effect; "supported" whether this system has them at all."""
    return ok(**_desktop_state(request))


@router.post("/api/desktop")
async def desktop_set(request: Request):
    """{minimizeToTray, closeToTray, startWithWindows, keepEngine}: any of them."""
    b = await body(request)
    await asyncio.to_thread(request.app.state.desktop_settings.update, b)
    return ok(**_desktop_state(request))


@router.post("/api/desktop/open")
async def desktop_open(request: Request):
    """{url}: opens a web page in the user's default browser. The app window is a separate browser
    profile, so a link opened inside it (the Chrome Web Store, for one) would land in the wrong place."""
    url = str((await body(request)).get("url") or "")
    if not re.match(r"^https?://[^\s]+$", url, re.I):
        return fail("BAD_URL", status=400)
    threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    return ok()


def _update_state(request: Request) -> dict:
    s = request.app.state.desktop_settings
    return {**request.app.state.updates.state(), "settings": {"checkUpdates": s["checkUpdates"], "autoUpdate": s["autoUpdate"]}}


@router.get("/api/update")
async def update_state(request: Request, force: str = "0"):
    """Newer releases and their notes (Settings -> Updates). Asks GitHub at most every few hours, or now
    with force=1; never when checking is turned off, unless forced."""
    if force == "1" or request.app.state.desktop_settings["checkUpdates"]:
        await asyncio.to_thread(request.app.state.updates.check, force == "1")
    return ok(**_update_state(request))


@router.post("/api/update/install")
async def update_install(request: Request):
    """Downloads and verifies the latest installer, starts it, and closes the desktop app so it can be
    replaced; the installer starts Tarjuman again. {force: true} goes ahead while jobs are running."""
    b = await body(request)
    d = request.app.state.desktop
    if d is None and updates.platform_kind() != "appimage":
        return fail("UPDATE_NEEDS_APP", "Update from the installed desktop app.")
    if services(request).jobs.running_count() and not b.get("force"):
        return fail("JOBS_RUNNING")
    # Windows: the installer replaces the program, so the app closes. Linux: the AppImage is replaced in place.
    if not request.app.state.updates.start_install(on_ready=(lambda: d.quit(confirm=False)) if d is not None else (lambda: None)):
        return fail("UPDATE_UNAVAILABLE")
    return ok(**_update_state(request))


@router.post("/api/desktop/quit")
async def desktop_quit(request: Request):
    """Quits the desktop app (window, engine and icon). The installer asks this before an update, so
    the files it replaces aren't in use. Running jobs are stopped."""
    d = request.app.state.desktop
    if d is None:
        return ok(quitting=False)
    threading.Thread(target=d.quit, kwargs={"confirm": False}, daemon=True).start()
    return ok(quitting=True)


@router.post("/api/desktop/show")
async def desktop_show(request: Request):
    """Brings the app window up. A second start of the app asks the running one this, then exits."""
    d = request.app.state.desktop
    if d is None:
        return ok(shown=False)
    threading.Thread(target=d.show_window, daemon=True).start()
    return ok(shown=True)


def _pair_links(request: Request) -> list[str]:
    code = request.app.state.pairing.current_code()
    port = request.app.state.port
    ip = lan_ip()
    return [f"http://{ip}:{port}/pair?code={code}"] if ip else []


def _pairing_state(request: Request) -> dict:
    links = _pair_links(request)
    p = request.app.state.pairing
    # codeExpires is in milliseconds, like the other times; 0 means the code doesn't run out.
    return {"links": links, "lan": bool(links), "devices": p.public(), "codeExpires": int(p.code_expires * 1000)}


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


# Seconds of 16 kHz mono s16le one live request may carry (the extension sends phrases of a few seconds).
LIVE_MAX_BYTES = 30 * 16000 * 2


@router.post("/api/live")
async def live(request: Request):
    """A few seconds of tab audio from the extension: transcribe, translate, and optionally speak."""
    b = await body(request)
    if not b.get("audio_b64"):
        return fail("NO_AUDIO", status=400)
    try:
        pcm = base64.b64decode(b["audio_b64"])
    except (binascii.Error, ValueError):
        return fail("NO_AUDIO", status=400)
    return await _live(request, pcm, b.get("tl") or "ar", bool(b.get("tts")), b.get("voice") or "")


@router.post("/api/live/raw")
async def live_raw(request: Request, tl: str = "ar", tts: str = "0", voice: str = ""):
    """The same as /api/live, with the audio as the raw request body (16 kHz mono s16le): a third smaller
    than base64 inside JSON, and nothing to encode or parse on either side."""
    pcm = bytearray()
    async for chunk in request.stream():
        pcm += chunk
        if len(pcm) > LIVE_MAX_BYTES:
            return fail("BODY_TOO_LARGE", status=413)
    if not pcm:
        return fail("NO_AUDIO", status=400)
    return await _live(request, bytes(pcm), tl or "ar", tts == "1", voice)


async def _live(request: Request, pcm: bytes, tl: str, tts: bool, voice: str):
    s = services(request)
    if not whisper_installed():
        return fail("WHISPER_NOT_INSTALLED")
    try:
        r = await s.whisper.transcribe_pcm(pcm)
    except Exception as e:  # noqa: BLE001
        return fail(getattr(e, "code", "ASR_ERROR"), str(e)[:300])
    text = " ".join(str(r["text"] or "").split())
    ar = ""
    if text:
        ar = (await s.translator.translate_many([text], sl=r["lang"] or "auto", tl=tl)).get(text, "")
    audio_b64 = audio_mime = ""
    if tts and ar:
        try:
            t = await s.tts.speak(ar, tl, voice)
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
