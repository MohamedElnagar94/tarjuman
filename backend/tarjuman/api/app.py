"""The FastAPI application: security checks, error shape, routes, and the web app's static files."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__, config, storage
from ..core import http
from ..core.errors import AppError
from ..services import Services
from .deps import fail
from .extensions import ExtensionTrust, extension_id
from .pairing import COOKIE, HEADER, Pairing
from .routes import ai, jobs, learn, media, system, videos
from .security import LOCAL_ONLY, OPEN_TO_ALL, is_loopback, post_allowed, request_allowed

log = logging.getLogger("tarjuman")

# Python reads MIME types from the Windows registry, where .js is often "text/plain"; browsers then
# refuse to run the web app's module scripts. Set the types the app serves explicitly.
for _ext, _type in {
    ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml",
    ".json": "application/json", ".woff2": "font/woff2", ".woff": "font/woff", ".webmanifest": "application/manifest+json",
}.items():
    mimetypes.add_type(_type, _ext)

NO_BUILD_PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Tarjuman</title>
<body style="font:16px system-ui;max-width:40rem;margin:4rem auto;padding:0 1rem;line-height:1.6">
<h1>Tarjuman is running</h1><p>The web app hasn't been built yet. Build it once with:</p>
<pre style="background:#eef;padding:1rem;border-radius:8px">npm --prefix frontend install
npm --prefix frontend run build</pre><p>then reload this page. The API is live at <code>/api/health</code>.</p></body></html>"""


PAIR_FAILED_PAGE = """<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ترجمان</title>
<body style="font:17px system-ui;max-width:34rem;margin:3rem auto;padding:0 1.2rem;line-height:1.8">
<h1 style="font-size:1.4rem">رمز الربط غير صالح</h1>
<p>ربما انتهت مدة الرمز أو أُعيد إنشاؤه. افتح ترجمان على الحاسوب، ثم «الإعدادات ← الهاتف»، وامسح رمز QR الجديد.</p>
<p dir="ltr" style="text-align:left;color:#555">This pairing code is no longer valid. On the computer, open Settings → Phone and scan the new QR code.</p>
</body></html>"""

PAIR_BLOCKED_PAGE = """<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ترجمان</title>
<body style="font:17px system-ui;max-width:34rem;margin:3rem auto;padding:0 1.2rem;line-height:1.8">
<h1 style="font-size:1.4rem">محاولات كثيرة برمز غير صحيح</h1>
<p>انتظر عشر دقائق، ثم امسح رمز QR الظاهر في «الإعدادات ← الهاتف» على الحاسوب.</p>
<p dir="ltr" style="text-align:left;color:#555">Too many wrong codes from this device. Wait ten minutes, then scan the QR code shown in Settings → Phone.</p>
</body></html>"""


def create_app(services: Services | None = None, *, port: int = config.DEFAULT_PORT, warm: bool = True) -> FastAPI:
    s = services or Services()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s.load()
        # Nothing is running yet, so whatever is in tmp/ was left by a job that was interrupted.
        await asyncio.to_thread(storage.clear_tmp)
        asyncio.ensure_future(asyncio.to_thread(s.tts.prune))
        if warm:
            asyncio.get_running_loop().call_later(1.5, lambda: asyncio.ensure_future(s.tts.warm_up()))
        yield
        s.jobs.cancel_all()
        s.flush()
        pairing.flush()
        await http.close()

    app = FastAPI(title="Tarjuman", version=__version__, lifespan=lifespan, docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json")
    app.state.services = s
    app.state.port = port
    pairing = app.state.pairing = Pairing(config.DATA / "pairing.json")
    pairing.load()
    trust = app.state.extensions = ExtensionTrust(config.DATA / "extensions.json")
    trust.load()

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            if not request_allowed(request.headers):
                return fail("FORBIDDEN_ORIGIN", status=403)
            ext = extension_id(request.headers.get("origin"))
            request.state.extension_allowed = not ext or trust.check(ext)
            if not request.state.extension_allowed and path not in OPEN_TO_ALL:
                return fail(
                    "EXTENSION_NOT_ALLOWED",
                    "هذه الإضافة غير مسموح لها. اسمح بها من «الإعدادات ← الإضافات» في تطبيق ترجمان.",
                    status=403,
                )
            ip = request.client.host if request.client else ""
            local = is_loopback(ip)
            # The settings hold an API key, and pairing hands out access: only from this computer.
            if (path in LOCAL_ONLY or path.startswith("/api/pairing")) and not local:
                return fail("LOCAL_ONLY", "لا يمكن تعديل هذه الإعدادات إلا من الحاسوب نفسه", status=403)
            # Another device on the Wi-Fi gets nothing until it is paired (see pairing.py).
            token = request.cookies.get(COOKIE) or request.headers.get(HEADER)
            device = None if local else pairing.device(token)
            if not local and device is None and pairing.is_legacy(token):
                # Paired with the first version's shared secret: give it its own key, no re-pairing.
                migrated = pairing.pair(request.headers.get("user-agent", ""), ip)
                device = pairing.device(migrated)
            else:
                migrated = None
            if device:
                pairing.seen(device, ip)
            request.state.paired = local or device is not None
            if not request.state.paired and path not in OPEN_TO_ALL:
                return fail("NOT_PAIRED", "هذا الجهاز غير مربوط بترجمان. امسح رمز الربط من إعدادات الحاسوب.", status=401)
            if request.method == "POST" and not post_allowed(path, request.headers.get("content-type")):
                return fail("JSON_REQUIRED", status=415)
            if migrated:
                res = await call_next(request)
                res.set_cookie(COOKIE, migrated, max_age=365 * 24 * 3600, httponly=True, samesite="lax")
                return res
        return await call_next(request)

    @app.exception_handler(AppError)
    async def app_error(_request: Request, e: AppError):
        status = 400 if e.code in ("BAD_JSON", "BODY_TOO_LARGE") else 200
        return JSONResponse({"ok": False, "code": e.code, "message": e.message}, status_code=status)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, e: Exception):
        # The details (which may hold a local path or an address) stay in the log. The client gets a
        # reference to quote, so the two can be matched.
        ref = secrets.token_hex(4)
        log.error("request failed [%s] %s %s", ref, request.method, request.url.path, exc_info=e)
        return JSONResponse(
            {"ok": False, "code": "ERROR", "message": f"حدث خطأ غير متوقع. المرجع في السجل: {ref}", "ref": ref},
            status_code=500,
        )

    for r in (system.router, videos.router, jobs.router, media.router, learn.router, ai.router):
        app.include_router(r)

    @app.get("/pair", include_in_schema=False)
    async def pair(request: Request, code: str = ""):
        """Opened once on a phone (from the QR code): gives this device its own key, then opens the app."""
        ip = request.client.host if request.client else ""
        if pairing.blocked(ip):
            return HTMLResponse(PAIR_BLOCKED_PAGE, status_code=429)
        if not pairing.valid_code(code):
            pairing.failed(ip)
            return HTMLResponse(PAIR_FAILED_PAGE, status_code=403)
        res = RedirectResponse("/", status_code=303)
        if pairing.device(request.cookies.get(COOKIE)) is None:  # scanning twice doesn't list it twice
            token = pairing.pair(request.headers.get("user-agent", ""), ip)
            res.set_cookie(COOKIE, token, max_age=365 * 24 * 3600, httponly=True, samesite="lax")
        return res

    dist = config.FRONTEND_DIST
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            return fail("NOT_FOUND", status=404)
        f = (dist / path).resolve()
        if path and f.is_file() and dist.resolve() in f.parents:
            return FileResponse(f)
        index = dist / "index.html"
        if index.exists():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return HTMLResponse(NO_BUILD_PAGE)

    return app
