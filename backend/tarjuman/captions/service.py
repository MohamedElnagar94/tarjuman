"""Get a video's cues for a target language: YouTube's own translation if it has one, otherwise the
source track (repaired), to be translated by us. Local media uses its Whisper transcript."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from .. import config
from ..core.errors import AppError
from ..core.text import is_media_link, media_id_of, norm_lang, parse_video_id
from urllib.parse import quote

from .chapters import parse_chapters
from .models import Cue, Line, VideoCues
from .repair import align_source, reconstruct_asr
from .youtube import fetch_track_lines, player_response

if TYPE_CHECKING:
    from ..media.library import MediaLibrary

TTL = 3600.0


class CaptionService:
    def __init__(self, media: "MediaLibrary"):
        self.media = media
        self._cache: dict[str, tuple[float, VideoCues]] = {}
        self._src_urls: dict[str, str] = {}  # video id -> its source caption track
        self._yt_translations: dict[str, list[Line]] = {}
        self._chapters: dict[str, tuple[float, list[dict]]] = {}  # video id -> (when, chapters)

    def cached(self) -> list[VideoCues]:
        return [d for _, d in self._cache.values()]

    def forget(self, video_id: str) -> None:
        for k in [k for k in self._cache if k.split("|", 1)[0] == video_id]:
            self._cache.pop(k, None)

    def put(self, data: VideoCues) -> None:
        self._cache[f"{data.videoId}|{norm_lang(data.tl)}"] = (time.time(), data)

    async def get(self, link: str, tl: str = "ar", *, fresh: bool = False) -> VideoCues:
        if is_media_link(link):
            return self._media_cues(str(link).strip(), tl)
        video_id = parse_video_id(link)
        if not video_id:
            raise AppError("BAD_URL")
        key = f"{video_id}|{norm_lang(tl)}"
        hit = self._cache.get(key)
        if not fresh and hit and time.time() - hit[0] < TTL:
            return hit[1]
        data = await self._from_youtube(video_id, tl)
        self._cache[key] = (time.time(), data)
        return data

    async def _from_youtube(self, video_id: str, tl: str) -> VideoCues:
        resp = await player_response(video_id)
        tracks = ((resp.get("captions") or {}).get("playerCaptionsTracklistRenderer") or {}).get("captionTracks") or []
        details = resp.get("videoDetails") or {}
        self._remember_chapters(video_id, details)
        title = details.get("title") or video_id
        author = details.get("author") or ""
        length = int(details.get("lengthSeconds") or 0)
        t = norm_lang(tl)

        def lang(x: dict) -> str:
            return norm_lang(x.get("languageCode"))

        target = next((x for x in tracks if lang(x) == t and not x.get("kind")), None) or next(
            (x for x in tracks if lang(x) == t), None
        )
        if config.FORCE_ASR:
            source = (
                next((x for x in tracks if x.get("kind") == "asr" and lang(x) == "en"), None)
                or next((x for x in tracks if x.get("kind") == "asr"), None)
                or (tracks[0] if tracks else None)
            )
        else:
            source = (
                next((x for x in tracks if lang(x) == "en" and not x.get("kind")), None)
                or next((x for x in tracks if lang(x) == "en"), None)
                or next((x for x in tracks if not x.get("kind")), None)
                or (tracks[0] if tracks else None)
            )
        if not target and not source:
            raise AppError("NO_CAPTIONS")

        if target:
            ar_lines = await fetch_track_lines(target["baseUrl"])
            src_lines = []
            if source and source is not target:
                try:
                    src_lines = await fetch_track_lines(source["baseUrl"])
                except Exception:  # noqa: BLE001 — the translation alone is still useful
                    src_lines = []
            src_text = align_source(ar_lines, src_lines)
            cues = [Cue(c.start, c.end, src_text[k] if k < len(src_text) else "", c.text) for k, c in enumerate(ar_lines)]
            return VideoCues(
                videoId=video_id, title=title, author=author, lengthSeconds=length, tl=t,
                alreadyTranslated=True, autoTranslated=target.get("kind") == "asr", asr=False,
                srcLang=lang(source) if source else "en", cues=cues,
            )

        self._src_urls[video_id] = source["baseUrl"]
        raw = await fetch_track_lines(source["baseUrl"])
        is_asr = source.get("kind") == "asr" or "kind=asr" in source.get("baseUrl", "")
        lines = reconstruct_asr(raw) if is_asr else raw
        return VideoCues(
            videoId=video_id, title=title, author=author, lengthSeconds=length, tl=t,
            alreadyTranslated=False, asr=is_asr, srcLang=lang(source) or "en",
            cues=[Cue(c.start, c.end, c.text, "") for c in lines],
        )

    def _media_cues(self, link: str, tl: str) -> VideoCues:
        m = self.media.get(media_id_of(link))
        if not m or not m.path.exists():
            raise AppError("NO_MEDIA", "هذا الفيديو غير موجود على الجهاز")
        if not m.segments:
            raise AppError("NO_CAPTIONS")
        key = f"{link}|{norm_lang(tl)}"
        hit = self._cache.get(key)
        if hit:
            return hit[1]
        data = VideoCues(
            videoId=link, title=m.title, author="", lengthSeconds=round(m.duration or 0), tl=norm_lang(tl),
            alreadyTranslated=False, asr=True, whisper=True, media=True, srcLang=m.lang or "auto",
            cues=[Cue(s["start"], s["end"], s["text"], "") for s in m.segments],
        )
        self._cache[key] = (time.time(), data)
        return data

    async def youtube_translation(self, video_id: str, tl: str) -> list[Line]:
        """YouTube's own machine translation of the source track (``tlang``). A fallback for when the
        translation services refuse or run out of quota; timed lines, not sentences."""
        key = f"{video_id}|{norm_lang(tl)}"
        if key in self._yt_translations:
            return self._yt_translations[key]
        url = self._src_urls.get(video_id)
        if not url:
            return []
        try:
            lines = await fetch_track_lines(f"{url}&tlang={quote(norm_lang(tl))}")
        except Exception:  # noqa: BLE001 — not every track can be translated
            return []
        self._yt_translations[key] = lines
        return lines

    def _remember_chapters(self, video_id: str, details: dict) -> list[dict]:
        found = parse_chapters(details.get("shortDescription") or "", float(details.get("lengthSeconds") or 0))
        self._chapters[video_id] = (time.time(), found)
        return found

    async def chapters(self, video_id: str) -> list[dict]:
        """The chapters the video's owner listed in its description ([] when none). Read with the
        captions, so usually there is no second request."""
        hit = self._chapters.get(video_id)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
        resp = await player_response(video_id)
        return self._remember_chapters(video_id, resp.get("videoDetails") or {})

    async def title(self, video_id: str) -> str:
        if is_media_link(video_id):
            m = self.media.get(media_id_of(video_id))
            return m.title if m else video_id
        from .youtube import video_title

        return await video_title(video_id)
