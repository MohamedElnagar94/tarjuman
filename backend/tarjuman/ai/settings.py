"""AI provider settings. The file holds an API key: owner-only, written atomically, never returned."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from ..core.store import read_json, write_json

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "provider": "anthropic",
    "apiKey": "",
    "model": "",
    "baseUrl": "",
    "style": "msa",
}


class AiSettings:
    def __init__(self, file: Path):
        self.file = file
        self.ai: dict[str, Any] = dict(DEFAULTS)
        self.stats = {"lines": 0, "failed": 0, "lastError": ""}
        self.on_change: list[Callable[[], None]] = []

    def load(self) -> None:
        j = read_json(self.file, {})
        self.ai = {**DEFAULTS, **(j.get("ai") or {})}

    def save(self) -> None:
        write_json(self.file, {"ai": self.ai}, private=True, indent=1)

    @property
    def api_key(self) -> str:
        if self.ai["apiKey"]:
            return self.ai["apiKey"]
        return os.environ.get("ANTHROPIC_API_KEY", "") if self.ai["provider"] == "anthropic" else ""

    @property
    def model(self) -> str:
        return self.ai["model"] or (DEFAULT_MODEL if self.ai["provider"] == "anthropic" else "")

    @property
    def ready(self) -> bool:
        a = self.ai
        if not a["enabled"]:
            return False
        if a["provider"] == "anthropic":
            return bool(self.api_key)
        return bool(a["baseUrl"] and a["model"])

    def public(self) -> dict[str, Any]:
        a = self.ai
        return {
            "ai": {
                "enabled": a["enabled"],
                "provider": a["provider"],
                "model": a["model"],
                "baseUrl": a["baseUrl"],
                "style": a["style"],
                "hasKey": bool(self.api_key),
                "keyHint": "…" + a["apiKey"][-4:] if a["apiKey"] else "",
                "defaultModel": DEFAULT_MODEL if a["provider"] == "anthropic" else "",
                "ready": self.ready,
                "stats": self.stats,
            }
        }

    def update(self, patch: dict[str, Any]) -> None:
        """A new key string replaces the key; ``None`` clears it; no key keeps it. Changing the provider
        or the server address clears the old key, so it is never sent to a server it wasn't entered for."""
        a = dict(self.ai)
        for k in ("enabled", "provider", "model", "baseUrl", "style"):
            if k in patch and patch[k] is not None:
                a[k] = bool(patch[k]) if k == "enabled" else str(patch[k] or "").strip()

        def target(x: dict) -> str:
            return x["provider"] + "|" + ("" if x["provider"] == "anthropic" else x["baseUrl"])

        new_key = patch.get("apiKey").strip() if isinstance(patch.get("apiKey"), str) else ""
        if "apiKey" in patch and patch["apiKey"] is None:
            a["apiKey"] = ""
        elif new_key:
            a["apiKey"] = new_key
        elif target(a) != target(self.ai):
            a["apiKey"] = ""
        if a["provider"] not in ("anthropic", "openai"):
            a["provider"] = "anthropic"
        if a["style"] not in ("msa", "egyptian"):
            a["style"] = "msa"
        self.ai = a
        self.save()
        for fn in self.on_change:
            fn()
