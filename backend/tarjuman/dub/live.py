"""Live dub plans: sentences for a stretch of the video, each with a measured voice clip and a pace."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from collections import OrderedDict
from dataclasses import dataclass, field

from ..ai.script import ScriptWriter
from ..ai.settings import AiSettings
from ..captions.models import Cue, Line, VideoCues
from ..captions.repair import align_source
from ..captions.service import CaptionService
from ..core.text import norm_lang
from ..translate.service import Translator, map_limit
from ..voice.catalog import resolve_voice
from ..voice.gate import NEXT, PLAY, URGENT, WARM
from ..voice.service import TtsService
from .planner import Block, group_dub_blocks, pace_blocks


@dataclass
class Plan:
    data: VideoCues | None
    cues_already_translated: bool
    src_lang: str
    blocks: list[Block] = field(default_factory=list)
    yt_text: list[str] | None = None  # YouTube's translation spread over the blocks (fallback)
    prepared: set[int] = field(default_factory=set)  # windows already being prepared in the background


# Only sentences this close to the start of a requested window are measured before answering. The
# voice service can take seconds per sentence; measuring a whole 45 s window first made the player wait
# (and play on silently). Later sentences use estimates now and are made when the player prefetches them.
MEASURE_SPAN = 20.0
# After answering, the next stretch is translated and measured in the background at the lowest priority.
PREPARE_SPAN = 30.0


class LivePlanner:
    def __init__(
        self,
        captions: CaptionService,
        translator: Translator,
        tts: TtsService,
        writer: ScriptWriter,
        ai: AiSettings,
    ):
        self.captions = captions
        self.translator = translator
        self.tts = tts
        self.writer = writer
        self.ai = ai
        self._plans: dict[str, Plan] = {}
        self._cue_plans: OrderedDict[str, Plan] = OrderedDict()
        # Natural (rate 0) speech length per "voice|text", measured from real clips.
        self.natural: dict[str, float] = {}
        translator.edit_listeners.append(self._on_edit)
        ai.on_change.append(self.reset_texts)
        tts.pronounce.on_change.append(self.natural.clear)  # durations were measured on the old wording

    # ---------------- invalidation ----------------

    def _on_edit(self, tl: str, src: str, ar: str) -> None:
        for data in self.captions.cached():
            if norm_lang(data.tl) == tl and not data.alreadyTranslated:
                for c in data.cues:
                    if c.src == src:
                        c.ar = ar
        for p in self._plans.values():
            for b in p.blocks:
                if src in b.parts:
                    b.text = None

    def reset_texts(self) -> None:
        """Settings changed (e.g. the AI writer): sentences are written again on next request."""
        for p in self._plans.values():
            for b in p.blocks:
                b.text = None

    # ---------------- plans ----------------

    async def plan_for(self, link: str, tl: str) -> Plan:
        data = await self.captions.get(link, tl)
        key = f"{data.videoId}|{norm_lang(tl)}"
        p = self._plans.get(key)
        if not p or p.data is not data:
            p = Plan(data, data.alreadyTranslated, data.srcLang, group_dub_blocks(data.cues, use_ar=data.alreadyTranslated))
            self._plans[key] = p
        return p

    def plan_for_cues(self, cues: list[Cue], sl: str, tl: str) -> Plan:
        """Captions taken by the extension from any website's player (Coursera, Udemy…)."""
        key = hashlib.sha1((tl + "|" + json.dumps([[c.start, c.src] for c in cues])).encode()).hexdigest()
        p = self._cue_plans.get(key)
        if not p:
            p = Plan(None, False, sl or "auto", group_dub_blocks(cues))
            self._cue_plans[key] = p
            if len(self._cue_plans) > 20:
                self._cue_plans.popitem(last=False)
        return p

    async def _fill_texts(self, plan: Plan, need: list[Block], voice: str, tl: str, priority: int = 2) -> None:
        l = norm_lang(tl)

        def edited(b: Block) -> bool:
            return any(self.translator.has_edit(l, p) for p in b.parts)

        # AI script: natural, spoken, sized to each sentence's time. Used even when YouTube has an Arabic
        # track — the model writes from the original speech, shorter and more natural than machine text.
        candidates = [b for b in need if b.src and not edited(b)]
        if self.ai.ready and candidates:
            v = resolve_voice(voice, tl)
            cps = self.tts.voice_cps(v)
            first = candidates[0].i
            context = [b.text for b in plan.blocks[max(0, first - 3) : first] if b.text]
            try:
                lines = await self.writer.write(
                    [{"src": b.src, "seconds": b.slot, "maxChars": max(8, math.floor(b.slot * cps * 1.1))} for b in candidates],
                    tl=l,
                    context=context,
                )
                for b in candidates:
                    if lines.get(b.src):
                        b.text = lines[b.src]
            except Exception:  # noqa: BLE001 — wrong key etc.: plain translation below
                pass

        if plan.cues_already_translated:
            for b in need:
                if b.text is None:
                    b.text = b.cueAr
            return
        # Sentences with a user-corrected line are built from the line translations, so the fix is spoken.
        whole = [b for b in need if b.text is None and not edited(b)]
        per_line = [b for b in need if b.text is None and edited(b)]
        found = await self.translator.translate_many(
            [b.src for b in whole] + [p for b in per_line for p in b.parts],
            sl=plan.src_lang or "auto",
            tl=tl,
            priority=priority,
        )
        for b in whole:
            if found.get(b.src):
                b.text = found[b.src]
        for b in per_line:
            parts = [found.get(p) for p in b.parts]
            if all(parts):
                b.text = " ".join(parts)  # type: ignore[arg-type]

        # The translators refused (rate limit, used-up quota): rather than going silent, speak YouTube's
        # own translation of the same captions, mapped onto the sentences by time.
        missing = [b for b in need if b.text is None]
        if missing and plan.data and not plan.data.media:
            if plan.yt_text is None:
                lines = await self.captions.youtube_translation(plan.data.videoId, l)
                if lines:
                    plan.yt_text = align_source([Line(b.start, b.end, "") for b in plan.blocks], lines)
            if plan.yt_text:
                for b in missing:
                    if plan.yt_text[b.i]:
                        b.text = plan.yt_text[b.i]

    async def blocks(
        self,
        plan: Plan,
        start: float,
        end: float,
        voice: str,
        tl: str,
        *,
        measure: bool = False,
        urgent: bool = False,
        background: bool = False,
    ) -> list[dict]:
        """Sentences between ``start`` and ``end``, paced. With ``measure``, the sentences near the start
        are synthesized once at their estimated rate and measured first, so the pace comes from real
        durations and the browser finds the audio already cached."""
        sel = [b for b in plan.blocks if b.start + b.slot >= start and b.start <= end]
        need = [b for b in sel if b.text is None]
        if need:
            await self._fill_texts(plan, need, voice, tl, NEXT if background else URGENT if urgent else PLAY)

        v = resolve_voice(voice, tl)
        ready = [b for b in sel if b.text]
        after = plan.blocks[ready[-1].i + 1] if ready and ready[-1].i + 1 < len(plan.blocks) else None
        rows = [{"i": b.i, "start": b.start, "end": b.end, "text": b.text, "src": b.src} for b in ready]
        follow = after.start if after else math.inf

        def nat_key(b: dict) -> str:
            return f"{v.voice}|{b['text']}"

        def estimate(b: dict) -> float:
            return self.natural.get(nat_key(b)) or self.tts.natural_duration(b["text"], v)

        # Pass 1: a first rhythm from estimates (or from durations measured earlier).
        first = pace_blocks(rows, estimate, follow)
        clip_rate: dict[int, int] = {}  # i -> the rate the cached clip was made at

        # Pass 2: synthesize each sentence once at its first rate and measure it. Character-count
        # estimates can be ±30% off (terms, spelled-out acronyms, pauses).
        if measure and v.engine == "edge":

            async def measure_one(p: dict) -> None:
                if nat_key(p) in self.natural:
                    return
                try:
                    prio = WARM if background else URGENT if urgent else NEXT
                    r = await self.tts.speak(p["text"], tl, voice, p["rate"], priority=prio)
                except Exception:  # noqa: BLE001
                    return
                if r.fallback or not r.duration:
                    return  # a fallback voice's duration is not the requested voice's
                self.natural[nat_key(p)] = r.duration * (1 + p["rate"] / 100)
                clip_rate[p["i"]] = p["rate"]

            span = end if background else start + MEASURE_SPAN
            await map_limit([p for p in first if p["start"] <= span], 4, measure_one)

        # Pass 3: the final rhythm from real durations. If it is close to the cached clip, the browser
        # corrects it while playing (±20% is barely audible); otherwise it asks for a new clip.
        result = []
        for b in pace_blocks(rows, estimate, follow):
            final_rate = b["rate"] if v.engine == "edge" else 0
            synth_rate, play_rate = final_rate, 1.0
            if b["i"] in clip_rate:
                ratio = (1 + final_rate / 100) / (1 + clip_rate[b["i"]] / 100)
                if 0.85 <= ratio <= 1.2:
                    synth_rate = clip_rate[b["i"]]
                    play_rate = round(ratio, 4)
            result.append(
                {
                    "i": b["i"],
                    "start": b["at"],  # the engine starts here (maybe a bit early inside a paragraph)
                    "slot": b["slot"],
                    "rate": final_rate,
                    "synthRate": synth_rate,
                    "playRate": play_rate,
                    "text": b["text"],
                    "src": b["src"],
                    "srcStart": b["start"],
                    "end": b["end"],
                }
            )

        # Sentences that need a clip at a new rate: make it in the background so it's ready when asked.
        if measure and v.engine == "edge" and not background:
            for b in result:
                if b["synthRate"] != clip_rate.get(b["i"]):
                    asyncio.ensure_future(self._warm(b["text"], tl, voice, b["synthRate"]))
        if measure and not background:
            asyncio.ensure_future(self._prepare(plan, end, voice, tl))
        return result

    async def _prepare(self, plan: Plan, start: float, voice: str, tl: str) -> None:
        """Translate and measure the stretch after ``start`` while the player is busy with this one."""
        key = int(start // 10)
        if key in plan.prepared:
            return
        plan.prepared.add(key)
        try:
            await self.blocks(plan, start, start + PREPARE_SPAN, voice, tl, measure=True, background=True)
        except Exception:  # noqa: BLE001 — the player asks for it later anyway
            plan.prepared.discard(key)

    async def _warm(self, text: str, tl: str, voice: str, rate: int) -> None:
        try:
            await self.tts.speak(text, tl, voice, rate, priority=WARM)
        except Exception:  # noqa: BLE001
            pass
