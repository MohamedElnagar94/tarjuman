"""Machine translation providers: Google's free gtx endpoint (batched) and MyMemory as a fallback."""

from __future__ import annotations

import asyncio
import re
import time
from urllib.parse import quote

from ..core import http

GT_ENDPOINTS = (
    "https://translate.googleapis.com/translate_a/single?client=gtx",
    "https://translate.google.com/translate_a/single?client=gtx",
)
# After a 429 Google is left alone for a while instead of being hammered: 30 s at first, doubling while
# it keeps refusing (up to 5 minutes), back to 30 s after the next success.
GT_BACKOFF_MIN = 30.0
GT_BACKOFF_MAX = 300.0


class Google:
    name = "google"

    def __init__(self) -> None:
        self.cool_until = 0.0
        self.backoff = GT_BACKOFF_MIN

    @property
    def cooling(self) -> bool:
        return time.time() < self.cool_until

    async def _request(self, text: str, sl: str, tl: str) -> str:
        if self.cooling:
            raise RuntimeError("GT_COOLDOWN")
        last: Exception | None = None
        for base in GT_ENDPOINTS:
            url = f"{base}&sl={quote(sl or 'auto')}&tl={quote(tl)}&dt=t&q={quote(text)}"
            try:
                j = await http.get_json(url, attempts=2, timeout=20)
                if isinstance(j, list) and j and isinstance(j[0], list):
                    out = "".join((x[0] or "") if isinstance(x, list) else "" for x in j[0])
                    if out.strip():
                        self.backoff = GT_BACKOFF_MIN
                        return out
                last = RuntimeError("GT_FORMAT")
            except http.HttpError as e:
                last = e
                if e.status == 429:
                    self.cool_until = time.time() + self.backoff
                    self.backoff = min(GT_BACKOFF_MAX, self.backoff * 2)
                    raise RuntimeError("GT_429") from e
            except Exception as e:  # noqa: BLE001
                last = e
        raise last or RuntimeError("TRANSLATE_FAILED")

    async def translate(self, text: str, sl: str, tl: str) -> str:
        return (await self._request(text, sl, tl)).strip()

    async def translate_batch(self, texts: list[str], sl: str, tl: str) -> list[str] | None:
        """Several lines in one request, joined by newlines — much faster and less likely to be
        blocked. Returns None when the line count doesn't survive, so the caller goes line by line."""
        if len(texts) == 1:
            return [await self.translate(texts[0], sl, tl)]
        joined = "\n".join(re.sub(r"\s*\n\s*", " ", t) for t in texts)
        out = [s.strip() for s in (await self._request(joined, sl, tl)).split("\n")]
        while len(out) > len(texts) and not out[-1]:
            out.pop()
        return out if len(out) == len(texts) and all(out) else None


class GoogleExtension(Google):
    """The endpoint Google's own Chrome translate extension uses. It has its own rate limit (it often
    still answers while ``gtx`` refuses) and takes many lines per request, one answer per line."""

    name = "google-ext"
    URL = "https://clients5.google.com/translate_a/t?client=dict-chrome-ex"

    async def _request_many(self, texts: list[str], sl: str, tl: str) -> list[str]:
        if self.cooling:
            raise RuntimeError("GT_COOLDOWN")
        query = "&".join("q=" + quote(t) for t in texts)
        try:
            j = await http.get_json(f"{self.URL}&sl={quote(sl or 'auto')}&tl={quote(tl)}&{query}", attempts=2, timeout=20)
        except http.HttpError as e:
            if e.status == 429:
                self.cool_until = time.time() + self.backoff
                self.backoff = min(GT_BACKOFF_MAX, self.backoff * 2)
                raise RuntimeError("GT_429") from e
            raise
        # sl=auto answers [[text, detected_lang], ...]; a fixed sl answers [text, ...].
        out = [(x[0] if isinstance(x, list) else x) for x in (j if isinstance(j, list) else [])]
        if len(out) != len(texts) or not all(isinstance(x, str) and x.strip() for x in out):
            raise RuntimeError("GT_FORMAT")
        self.backoff = GT_BACKOFF_MIN
        return [x.strip() for x in out]

    async def translate(self, text: str, sl: str, tl: str) -> str:
        return (await self._request_many([text], sl, tl))[0]

    async def translate_batch(self, texts: list[str], sl: str, tl: str) -> list[str] | None:
        return await self._request_many(texts, sl, tl)


# MyMemory refuses a query longer than 500 bytes of UTF-8 (an Arabic letter is two bytes).
MYMEMORY_MAX_BYTES = 480


def split_bytes(text: str, limit: int) -> list[str]:
    """``text`` in pieces of at most ``limit`` UTF-8 bytes, cut after a sentence when there is one,
    else between words. Only a single word longer than the limit is cut inside. Nothing is dropped."""
    pieces: list[str] = []
    rest = text.strip()
    while len(rest.encode()) > limit:
        head = rest.encode()[:limit].decode("utf-8", "ignore")  # never ends inside a character
        ends = [m.end() for m in re.finditer(r"[.!?؟。…؛;]+(?=\s)", head)]
        cut = ends[-1] if ends and ends[-1] > len(head) // 3 else head.rfind(" ")
        if cut <= 0:
            cut = len(head)
        pieces.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        pieces.append(rest)
    return pieces


class MyMemory:
    async def translate(self, text: str, sl: str, tl: str) -> str:
        src = (sl if sl and sl != "auto" else "en").split("-")[0]
        tgt = (tl or "ar").split("-")[0]
        parts = []
        for q in split_bytes(text, MYMEMORY_MAX_BYTES):
            url = f"https://api.mymemory.translated.net/get?q={quote(q)}&langpair={quote(src + '|' + tgt)}"
            j = await http.get_json(url, attempts=2, timeout=15)
            out = str(((j or {}).get("responseData") or {}).get("translatedText") or "").strip()
            if not out:
                raise RuntimeError("MYMEMORY_EMPTY")
            if re.search(r"MYMEMORY WARNING|QUOTA|INVALID", out, re.I):
                raise RuntimeError("MYMEMORY_QUOTA")
            parts.append(out)
            await asyncio.sleep(0.12)
        return " ".join(parts)
