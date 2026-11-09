"""YouTube InnerTube: video details and caption tracks, without an API key or cookies."""

from __future__ import annotations

from typing import Any

from ..core import http
from ..core.errors import AppError
from .models import Line
from .parse import parse_captions
from .repair import normalize_lines, unroll_lines

INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

# Tried in order: different clients get different answers for age-gated or region-locked videos.
CLIENTS: list[dict[str, Any]] = [
    {"clientName": "ANDROID", "clientVersion": "20.05.46", "androidSdkVersion": 30},
    {"clientName": "IOS", "clientVersion": "20.10.4", "deviceModel": "iPhone16,2"},
    {"clientName": "WEB", "clientVersion": "2.20241126.01.00"},
]


def _context(client: dict[str, Any]) -> dict[str, Any]:
    c = {"clientName": client["clientName"], "clientVersion": client["clientVersion"], "hl": "en", "gl": "US"}
    for k in ("androidSdkVersion", "deviceModel"):
        if k in client:
            c[k] = client[k]
    return {"context": {"client": c, "user": {"lockedSafetyMode": False}, "request": {"useSsl": True}}}


async def player_response(video_id: str) -> dict[str, Any]:
    last: Exception | None = None
    for client in CLIENTS:
        try:
            res = await http.request(
                "POST",
                INNERTUBE_URL,
                json={**_context(client), "videoId": video_id},
                headers={"Origin": "https://www.youtube.com"},
            )
            j = res.json()
            if j and j.get("videoDetails"):
                return j
            ps = (j or {}).get("playabilityStatus") or {}
            last = AppError("UNPLAYABLE", f"{ps.get('status', 'unknown')} {ps.get('reason', '')}".strip())
        except Exception as e:  # noqa: BLE001 — try the next client
            last = e
    raise last or AppError("UNPLAYABLE")


async def fetch_track_lines(base_url: str) -> list[Line]:
    lines = parse_captions(await http.get_text(base_url))
    if not lines:
        raise AppError("CAPTIONS_EMPTY")
    return unroll_lines(normalize_lines(lines))


async def video_title(video_id: str) -> str:
    try:
        return ((await player_response(video_id)).get("videoDetails") or {}).get("title") or video_id
    except Exception:  # noqa: BLE001
        return video_id
