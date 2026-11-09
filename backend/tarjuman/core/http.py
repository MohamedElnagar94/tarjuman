"""One shared HTTP client with retries for every outbound call (YouTube, translators, voices)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..config import UA

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"},
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


class HttpError(Exception):
    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retryable = status == 429 or status >= 500


async def request(
    method: str,
    url: str,
    *,
    attempts: int = 3,
    timeout: float = 25.0,
    **kwargs: Any,
) -> httpx.Response:
    """Send a request, retrying network errors, 429 and 5xx with exponential backoff."""
    last: Exception | None = None
    for i in range(attempts):
        try:
            res = await client().request(method, url, timeout=timeout, **kwargs)
            if res.status_code >= 400:
                err = HttpError(res.status_code)
                if not err.retryable:
                    raise err
                last = err
            else:
                return res
        except HttpError as e:
            if not e.retryable:
                raise
            last = e
        except (httpx.TransportError, httpx.TimeoutException) as e:
            last = e
        if i < attempts - 1:
            await asyncio.sleep(0.5 * 2**i)
    assert last is not None
    raise last


async def get_text(url: str, **kwargs: Any) -> str:
    return (await request("GET", url, **kwargs)).text


async def get_json(url: str, **kwargs: Any) -> Any:
    return (await request("GET", url, **kwargs)).json()


async def get_bytes(url: str, **kwargs: Any) -> bytes:
    return (await request("GET", url, **kwargs)).content


async def download(url: str, dest, *, timeout: float = 300.0) -> None:
    """Stream a large file to disk (models), via a .part file."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    async with client().stream("GET", url, timeout=timeout) as res:
        if res.status_code >= 400:
            raise HttpError(res.status_code)
        with open(part, "wb") as fh:
            async for chunk in res.aiter_bytes(1 << 16):
                fh.write(chunk)
    part.replace(dest)
