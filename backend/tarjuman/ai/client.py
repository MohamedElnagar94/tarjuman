"""One structured (JSON) request to the configured model: Claude through the official SDK, or any
OpenAI-compatible server (Gemini, Groq, OpenRouter, Ollama, LM Studio).

``context`` is a large fixed block such as the video transcript. With Claude it goes first in the
system prompt and is marked for prompt caching, so later questions about the same video are cheaper
and faster."""

from __future__ import annotations

import json
import re
from typing import Any

from ..core import http
from ..core.errors import AppError
from .settings import AiSettings

# Models that support the server-side refusal fallback (`fallbacks: "default"`).
_FALLBACK_MODELS = re.compile(r"^claude-(opus-5|fable-5|sonnet-5-5)")


def strip_fences(s: str) -> str:
    s = re.sub(r"^\s*```(?:json)?\s*", "", str(s or ""), flags=re.I)
    return re.sub(r"\s*```\s*$", "", s)


class AiClient:
    def __init__(self, settings: AiSettings):
        self.settings = settings

    async def complete(
        self,
        system: str,
        user: str,
        *,
        schema: dict[str, Any],
        shape: str,
        effort: str = "low",
        context: str = "",
    ) -> dict[str, Any]:
        if self.settings.ai["provider"] == "anthropic":
            return await self._anthropic(system, user, schema=schema, effort=effort, context=context)
        return await self._openai_compatible(system, user, shape=shape, context=context)

    async def _anthropic(self, system: str, user: str, *, schema, effort: str, context: str) -> dict[str, Any]:
        try:
            import anthropic
        except ImportError as e:
            raise AppError("AI_SDK_MISSING", "مكتبة Claude مش متسطّبة — شغّل: python -m tarjuman setup") from e

        model = self.settings.model
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": 16000,
            "system": (
                [
                    {"type": "text", "text": context, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": system},
                ]
                if context
                else system
            ),
            "messages": [{"role": "user", "content": user}],
            "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        }
        client = anthropic.AsyncAnthropic(api_key=self.settings.api_key or None, timeout=180.0, max_retries=2)
        try:
            if _FALLBACK_MODELS.match(model):
                # If the model declines, the API re-runs the request on a suitable fallback model.
                res = await client.beta.messages.create(
                    **params, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                )
            else:
                res = await client.messages.create(**params)
        except anthropic.AuthenticationError as e:
            raise AppError("AI_AUTH", "مفتاح Claude غلط أو مش موجود") from e
        except anthropic.RateLimitError as e:
            raise AppError("AI_RATE_LIMIT", "Claude: وصلت للحد المسموح — استنى شوية") from e
        except anthropic.APIStatusError as e:
            raise AppError("AI_HTTP", f"Claude {e.status_code}: {e.message}"[:300]) from e
        except anthropic.APIError as e:
            raise AppError("AI_NETWORK", str(e)[:200]) from e
        finally:
            await client.close()

        if res.stop_reason == "refusal":
            raise AppError("AI_REFUSED", "الموديل رفض الطلب")
        if res.stop_reason == "max_tokens":
            raise AppError("AI_TRUNCATED", "الرد اتقطع")
        text = "".join(b.text for b in res.content if b.type == "text")
        return json.loads(text)

    async def _openai_compatible(self, system: str, user: str, *, shape: str, context: str) -> dict[str, Any]:
        a = self.settings.ai
        base = str(a["baseUrl"] or "").rstrip("/")
        headers = {"Content-Type": "application/json"}
        if a["apiKey"]:
            headers["Authorization"] = f"Bearer {a['apiKey']}"
        body = {
            "model": a["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (context + "\n\n" if context else "") + system + "\n\nAnswer with JSON only, in this shape: " + shape,
                },
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            res = await http.client().post(base + "/chat/completions", json=body, headers=headers, timeout=180.0)
        except Exception as e:  # noqa: BLE001
            raise AppError("AI_NETWORK", str(e)[:200]) from e
        try:
            j = res.json()
        except ValueError:
            j = {}
        if res.status_code >= 400:
            msg = ((j.get("error") or {}).get("message") if isinstance(j, dict) else None) or f"HTTP {res.status_code}"
            raise AppError("AI_AUTH" if res.status_code == 401 else "AI_HTTP", str(msg)[:300])
        content = (((j.get("choices") or [{}])[0]).get("message") or {}).get("content")
        return json.loads(strip_fences(content))
