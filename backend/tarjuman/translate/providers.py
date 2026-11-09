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
# After a 429 Google is left alone for a while instead of being hammered.
GT_COOLDOWN = 300.0


class Google:
    def __init__(self) -> None:
        self.cool_until = 0.0

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
                        return out
                last = RuntimeError("GT_FORMAT")
            except http.HttpError as e:
                last = e
                if e.status == 429:
                    self.cool_until = time.time() + GT_COOLDOWN
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


class MyMemory:
    async def translate(self, text: str, sl: str, tl: str) -> str:
        src = (sl if sl and sl != "auto" else "en").split("-")[0]
        tgt = (tl or "ar").split("-")[0]
        q = text[:480]
        url = f"https://api.mymemory.translated.net/get?q={quote(q)}&langpair={quote(src + '|' + tgt)}"
        j = await http.get_json(url, attempts=2, timeout=15)
        out = str(((j or {}).get("responseData") or {}).get("translatedText") or "").strip()
        if not out:
            raise RuntimeError("MYMEMORY_EMPTY")
        if re.search(r"MYMEMORY WARNING|QUOTA|INVALID", out, re.I):
            raise RuntimeError("MYMEMORY_QUOTA")
        await asyncio.sleep(0.12)
        return out
