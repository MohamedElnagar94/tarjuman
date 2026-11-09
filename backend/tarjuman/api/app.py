"""The FastAPI application: security checks, error shape, routes, and the web app's static files."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__, config
from ..core import http
from ..core.errors import AppError
from ..services import Services
from .deps import fail
from .routes import ai, jobs, learn, media, system, videos
from .security import LOCAL_ONLY, is_loopback, post_allowed, request_allowed

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


def create_app(services: Services | None = None, *, port: int = config.DEFAULT_PORT, warm: bool = True) -> FastAPI:
    s = services or Services()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s.load()
        if warm:
            asyncio.get_running_loop().call_later(1.5, lambda: asyncio.ensure_future(s.tts.warm_up()))
        yield
        s.jobs.cancel_all()
        s.flush()
        await http.close()

    app = FastAPI(title="Tarjuman", version=__version__, lifespan=lifespan, docs_url="/api/docs", redoc_url=None,
                  openapi_url="/api/openapi.json")
    app.state.services = s
    app.state.port = port

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            if not request_allowed(request.headers):
                return fail("FORBIDDEN_ORIGIN", status=403)
            # The settings hold an API key: only from this computer, not from others on the Wi-Fi.
            if path in LOCAL_ONLY and not is_loopback(request.client.host if request.client else None):
                return fail("LOCAL_ONLY", "لا يمكن تعديل هذه الإعدادات إلا من الحاسوب نفسه", status=403)
            if request.method == "POST" and not post_allowed(path, request.headers.get("content-type")):
                return fail("JSON_REQUIRED", status=415)
        return await call_next(request)

    @app.exception_handler(AppError)
    async def app_error(_request: Request, e: AppError):
        status = 400 if e.code in ("BAD_JSON", "BODY_TOO_LARGE") else 200
        return JSONResponse({"ok": False, "code": e.code, "message": e.message}, status_code=status)

    @app.exception_handler(Exception)
    async def unexpected(_request: Request, e: Exception):
        log.exception("request failed")
        return JSONResponse({"ok": False, "code": "ERROR", "message": str(e)[:300]}, status_code=500)

    for r in (system.router, videos.router, jobs.router, media.router, learn.router, ai.router):
        app.include_router(r)

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
