from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx

from .. import config
from .errors import AppError

MAX_REDIRECTS = 5


def lan_ip() -> str | None:
    """This computer's address on the local network (no packet is actually sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def is_public(ip: str) -> bool:
    """False for this computer, the local network, link-local (cloud metadata) and reserved ranges."""
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return a.is_global and not a.is_multicast


async def resolve(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({i[4][0] for i in infos})


async def next_hop(url: str) -> str | None:
    """Where ``url`` redirects to, if it does. Only the headers are read."""
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=6) as c:
            async with c.stream("GET", url) as r:
                loc = r.headers.get("location") if r.is_redirect else None
                return urljoin(url, loc) if loc else None
    except (httpx.HTTPError, OSError):
        return None  # the downloader will report what is wrong with the link


async def ensure_public_url(url: str) -> None:
    """Refuses a link that points, directly or through redirects, at this computer or the local
    network: a download must not be a way to reach what only this network can reach."""
    if config.FETCH_PRIVATE:
        return
    for _ in range(MAX_REDIRECTS + 1):
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise AppError("BAD_URL")
        try:
            addresses = await resolve(parts.hostname)
        except OSError:
            raise AppError("BAD_URL") from None
        if not addresses or not all(is_public(a) for a in addresses):
            raise AppError("URL_NOT_ALLOWED", "هذا الرابط يشير إلى عنوان داخل شبكتك المحلية، ولا يُنزَّل منه.")
        nxt = await next_hop(url)
        if not nxt:
            return
        url = nxt
    raise AppError("BAD_URL")
