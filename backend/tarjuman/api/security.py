"""Request checks for the local API (docs/specs.md §3).

Any web page can send requests to 127.0.0.1, so requests from other sites are refused, and so are
domain names in the Host header (DNS rebinding)."""

from __future__ import annotations

import re
from typing import Mapping
from urllib.parse import urlsplit

_EXT_ORIGIN = re.compile(r"^(chrome|moz|edge)-extension://")
LOCAL_ONLY = frozenset(
    {"/api/settings", "/api/ai/test", "/api/pairing", "/api/pairing/reset", "/api/extensions", "/api/extensions/set",
     "/api/storage/clear", "/api/desktop", "/api/desktop/show", "/api/desktop/open", "/api/update", "/api/update/install"}
)
# Answered for unpaired devices too, so a phone can show "pair this device" instead of an error.
OPEN_TO_ALL = frozenset({"/api/health"})


def request_allowed(headers: Mapping[str, str]) -> bool:
    host = str(headers.get("host") or "")
    host_name = re.sub(r":\d+$", "", host).strip("[]")
    if not (host_name == "localhost" or re.fullmatch(r"[\d.]+", host_name) or ":" in host_name):
        return False
    origin = headers.get("origin")
    if origin and _EXT_ORIGIN.match(origin):
        return True
    if origin:
        try:
            return urlsplit(origin).netloc == host
        except ValueError:
            return False
    return headers.get("sec-fetch-site") != "cross-site"


def is_loopback(ip: str | None) -> bool:
    return str(ip or "") in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def post_allowed(path: str, content_type: str | None) -> bool:
    """POSTs must be JSON (HTML forms on other sites can't send it without a preflight); uploads are raw bytes."""
    ct = str(content_type or "").lower()
    if ct.startswith("application/json"):
        return True
    return path == "/api/media/upload" and ct.startswith("application/octet-stream")
