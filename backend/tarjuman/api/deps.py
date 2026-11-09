"""Helpers shared by the route modules."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse

from ..core.errors import AppError

if TYPE_CHECKING:
    from ..services import Services

BODY_LIMIT = 8_000_000


def services(request: Request) -> "Services":
    return request.app.state.services


async def body(request: Request) -> dict[str, Any]:
    raw = b""
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > BODY_LIMIT:
            raise AppError("BODY_TOO_LARGE")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError as e:
        raise AppError("BAD_JSON") from e
    if not isinstance(data, dict):
        raise AppError("BAD_JSON")
    return data


def ok(**data: Any) -> JSONResponse:
    return JSONResponse({"ok": True, **data}, headers={"Cache-Control": "no-store"})


def fail(code: str, message: str | None = None, status: int = 200) -> JSONResponse:
    return JSONResponse({"ok": False, "code": code, "message": message or code}, status_code=status,
                        headers={"Cache-Control": "no-store"})


def content_disposition(name: str, download: bool) -> str:
    ascii_name = "".join(ch if 0x20 <= ord(ch) < 0x7F else "_" for ch in name).replace('"', "")
    kind = "attachment" if download else "inline"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


def qnum(value: str | None, default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default
