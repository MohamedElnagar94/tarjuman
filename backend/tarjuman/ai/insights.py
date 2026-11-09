"""Ask the video: a summary with chapters, and answers that point to moments in the video."""

from __future__ import annotations

from ..captions.models import VideoCues
from ..core.errors import AppError
from ..core.text import mmss
from ..voice.catalog import LANG_LABEL
from .client import AiClient
from .settings import AiSettings

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "points": {"type": "array", "items": {"type": "string"}},
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"start": {"type": "number"}, "title": {"type": "string"}},
                "required": ["start", "title"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "points", "chapters"],
    "additionalProperties": False,
}
SUMMARY_SHAPE = '{"summary":"...","points":["..."],"chapters":[{"start":0,"title":"..."}]}'

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "moments": {"type": "array", "items": {"type": "number"}}},
    "required": ["answer", "moments"],
    "additionalProperties": False,
}
ANSWER_SHAPE = '{"answer":"...","moments":[12.5]}'


def reply_lang(tl: str) -> str:
    return "Egyptian-friendly simple Modern Standard Arabic" if tl == "ar" else LANG_LABEL.get(tl, tl)


def transcript_context(data: VideoCues) -> str:
    """The transcript with timestamps — sent as a fixed, cacheable block."""
    lines = [f"[{mmss(c.start)} = {round(c.start)}s] {c.src or c.ar}" for c in data.cues if c.src or c.ar]
    title = str(data.title or "").replace('"', "'")
    return f'<video title="{title}">\n<transcript>\n' + "\n".join(lines) + "\n</transcript>\n</video>"


class Insights:
    def __init__(self, settings: AiSettings, client: AiClient):
        self.settings = settings
        self.client = client
        self._summaries: dict[str, dict] = {}

    def _need_ready(self) -> None:
        if not self.settings.ready:
            raise AppError("AI_NOT_READY", "فعّل الذكاء الاصطناعي وحط المفتاح الأول")

    async def summary(self, data: VideoCues, tl: str) -> dict:
        self._need_ready()
        key = f"{data.videoId}|{tl}|{self.settings.model}"
        if key in self._summaries:
            return self._summaries[key]
        system = "\n".join(
            [
                f"Summarize the video transcript above for a viewer, written in {reply_lang(tl)}.",
                "- summary: 3 to 5 sentences on what the video covers and why it matters.",
                "- points: the 5 to 8 most useful takeaways, each one short sentence.",
                "- chapters: split the whole video into logical chapters (about one per 3 to 10 minutes, at least 3 "
                "when the video is long enough). start is the chapter's start time in seconds, taken from the "
                "[.. = Ns] markers; title is a short label.",
                "Keep product and technical names in their usual Latin spelling.",
            ]
        )
        res = await self.client.complete(
            system,
            "Write the summary, points and chapters.",
            schema=SUMMARY_SCHEMA,
            shape=SUMMARY_SHAPE,
            effort="medium",
            context=transcript_context(data),
        )
        chapters = []
        for c in res.get("chapters") or []:
            title = str(c.get("title") or "")
            if title:
                try:
                    start = max(0.0, float(c.get("start") or 0))
                except (TypeError, ValueError):
                    start = 0.0
                chapters.append({"start": start, "title": title})
        out = {
            "summary": str(res.get("summary") or ""),
            "points": [str(p) for p in (res.get("points") or [])][:12],
            "chapters": sorted(chapters, key=lambda c: c["start"]),
        }
        self._summaries[key] = out
        return out

    async def ask(self, data: VideoCues, tl: str, question: str) -> dict:
        self._need_ready()
        q = str(question or "").strip()[:600]
        if not q:
            raise AppError("NO_QUESTION")
        system = "\n".join(
            [
                f"Answer the viewer's question about the video above, in {reply_lang(tl)}.",
                "Base the answer only on the transcript. If the video does not cover it, say so plainly.",
                "Keep it short and direct. moments: up to 3 times in seconds (from the [.. = Ns] markers) where the "
                "video talks about this, most relevant first.",
            ]
        )
        res = await self.client.complete(
            system, q, schema=ANSWER_SCHEMA, shape=ANSWER_SHAPE, effort="low", context=transcript_context(data)
        )
        moments = []
        for m in res.get("moments") or []:
            try:
                if float(m) >= 0:
                    moments.append(float(m))
            except (TypeError, ValueError):
                pass
        return {"answer": str(res.get("answer") or ""), "moments": moments[:3]}
