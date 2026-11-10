"""The long jobs: Whisper transcription, dubbed MP4, subtitled MP4, playlist batches, downloads."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from .. import config
from ..captions.formats import to_srt
from ..captions.models import Cue, VideoCues
from ..core import http
from ..core.errors import AppError, Cancelled
from ..core.text import is_media_link, media_id_of, norm_lang, safe_name, video_key, work_id
from ..dub.live import Plan
from ..dub.planner import PACE, fit_rate, group_dub_blocks, pace_blocks, split_speakers
from ..media import ytdlp
from ..media.ffmpeg import ffmpeg_exe
from ..translate.service import map_limit
from ..voice.catalog import Voice, resolve_voice
from .manager import Job, ProcError, run_proc

if TYPE_CHECKING:
    from ..services import Services

# A sentence may run this many seconds into the next one's time; the next one shifts by the same
# amount, so the delay doesn't accumulate.
DUB_SPILL = 0.7
QUALITIES = (480, 720, 1080)


def _quality(v) -> int:
    try:
        q = int(v)
    except (TypeError, ValueError):
        return 720
    return q if q in QUALITIES else 720


def _fresh_dir(path: Path) -> Path:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _media_file(s: "Services", link: str) -> Path:
    m = s.media.get(media_id_of(link))
    if not m or not m.path.exists():
        raise AppError("NO_MEDIA", "هذا الفيديو غير موجود على الجهاز")
    return m.path


def _need_key(link: str) -> str:
    key = video_key(link)
    if not key:
        raise AppError("BAD_URL")
    return key


def _need_python_tools() -> None:
    try:
        import yt_dlp  # noqa: F401
    except ImportError as e:
        raise AppError("PY_NOT_INSTALLED", "مكوّنات Python غير مثبّتة. شغّل: python -m tarjuman setup") from e


async def _download_video(s: "Services", job: Job, link: str, work: Path, quality: int, scale: float, base: float) -> Path:
    if is_media_link(link):
        return _media_file(s, link)
    return await ytdlp.download(
        job, link, work, "video", ytdlp.mp4_format(quality), merge_mp4=True,
        on_progress=lambda pct: setattr(job, "progress", max(1, round(base + pct * scale))),
    )


# ------------------------------------------------------------------ Whisper


def start_whisper(s: "Services", link: str, tl: str = "ar") -> str:
    from ..asr import installed

    if not installed():
        raise AppError("WHISPER_NOT_INSTALLED")
    key = _need_key(link)
    existing = s.jobs.find_active("whisper", key)
    if existing:
        return existing.id
    job = s.jobs.new("whisper", key, tl=norm_lang(tl) or "ar")
    s.jobs.start(job, lambda j: run_whisper(s, j, link))
    return job.id


async def run_whisper(s: "Services", job: Job, link: str) -> None:
    tmp = _fresh_dir(config.TMP / f"whisper-{work_id(job.videoId)}")
    media = s.media.get(media_id_of(link)) if is_media_link(link) else None
    tl = job.opts["tl"]
    try:
        if media:
            audio = _media_file(s, link)  # Whisper decodes any video/audio file directly
        else:
            job.phase = "تنزيل الصوت من يوتيوب"
            audio = await ytdlp.download(
                job, link, tmp, "audio", "bestaudio/best",
                on_progress=lambda pct: setattr(job, "progress", max(1, round(pct * 0.3))),
            )
        job.progress = 30
        job.check()

        job.phase = "تفريغ الصوت (Whisper)"
        res = await s.whisper.transcribe_file(
            audio, lambda p: setattr(job, "progress", 30 + round(p * 50)), lambda: job.cancelled
        )
        job.check()
        segments, lang = res["segments"], res["lang"]
        if not segments:
            raise AppError("NO_SPEECH", "لا يوجد كلام مفهوم في الفيديو")
        job.progress = 80

        job.phase = "ترجمة النص"
        cues = [Cue(x["start"], x["end"], x["text"], "") for x in segments if x["text"].strip()]
        await s.translator.translate_cues(
            cues, tl=tl, sl=lang or "auto",
            on_progress=lambda d, t: setattr(job, "progress", 80 + round(d / max(t, 1) * 20)),
        )
        if media:
            # The transcript is saved with the video: next time it opens instantly.
            media.segments, media.lang = segments, lang or ""
            media.duration = segments[-1]["end"] if segments else 0
            s.media.save()
        title = await s.captions.title(job.videoId)
        s.captions.put(
            VideoCues(
                videoId=job.videoId, title=title, author="", lengthSeconds=round(res.get("duration") or 0), tl=tl,
                alreadyTranslated=False, asr=True, whisper=True, media=bool(media), srcLang=lang or "", cues=cues,
            )
        )
        job.title = title
        job.extra.update(cues=[c.to_dict() for c in cues], srcLang=lang or "", tl=tl)
        job.progress = 100
        job.phase = "اكتمل"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ dubbed MP4


def start_dub(s: "Services", link: str, opts: dict) -> str:
    key = _need_key(link)
    _need_python_tools()
    existing = s.jobs.find_active("dub", key)
    if existing:
        return existing.id
    job = s.jobs.new("dub", key, **dub_options(opts))
    s.jobs.start(job, lambda j: run_dub(s, j, link))
    return job.id


def dub_options(o: dict) -> dict:
    try:
        bg = float(o.get("bgVolume") if o.get("bgVolume") is not None else 0.15)
    except (TypeError, ValueError):
        bg = 0.15
    return {
        "lang": norm_lang(o.get("lang")) or "ar",
        "voice": str(o.get("voice") or "auto"),
        "matchVoice": o.get("matchVoice") is not False,
        "bgVolume": min(1.0, max(0.0, bg)),
        "embedSubs": o.get("embedSubs") is not False,
        "burnSubs": bool(o.get("burnSubs")),
        "removeVoice": bool(o.get("removeVoice")),
        "quality": _quality(o.get("quality")),
    }


async def _ensure_separation_model(job: Job) -> None:
    if config.SEP_MODEL.exists():
        return
    job.extra["note"] = "جارٍ تنزيل نموذج فصل الصوت (نحو 65 ميغابايت) لمرة واحدة فقط"
    await http.download(config.SEP_MODEL_URL, config.SEP_MODEL)
    job.extra["note"] = ""


async def _separate_background(job: Job, video: Path, work: Path) -> Path:
    """A WAV of the background with the speech removed."""
    await _ensure_separation_model(job)
    out = work / "background.wav"

    def on_line(line: str) -> None:
        try:
            p = json.loads(line).get("progress")
        except ValueError:
            return
        if p is not None:
            job.extra["sepProgress"] = round(p * 100)

    await run_proc(
        job,
        [config.PYTHON, "-m", "tarjuman.media.separator", "--model", str(config.SEP_MODEL), "--input", str(video), "--out", str(out)],
        on_line=on_line,
    )
    return out


async def _sentence_pitches(job: Job, video: Path, work: Path, blocks) -> list[float]:
    """The original speaker's pitch during each sentence (0 = unclear)."""
    ranges = work / "ranges.json"
    ranges.write_text(json.dumps([[b.start, b.end] for b in blocks]), encoding="utf-8")
    try:
        out = await run_proc(job, [config.PYTHON, "-m", "tarjuman.media.pitch", str(video), str(ranges)])
        f0 = json.loads(out.strip().splitlines()[-1]).get("f0") or []
        return [float(f0[k]) if k < len(f0) else 0.0 for k in range(len(blocks))]
    except Cancelled:
        raise
    except Exception:  # noqa: BLE001
        return [0.0] * len(blocks)


async def run_dub(s: "Services", job: Job, link: str) -> None:
    o = job.opts
    work = _fresh_dir(config.TMP / "dub" / work_id(job.videoId))
    try:
        job.phase = "تنزيل الفيديو"
        video = await _download_video(s, job, link, work, o["quality"], 0.2, 0)
        job.progress = 20
        job.check()

        # Removing the speaker runs on the CPU in parallel with voice synthesis (which waits on the network).
        sep_task = None
        if o["removeVoice"]:

            async def separate() -> Path | None:
                try:
                    return await _separate_background(job, video, work)
                except Cancelled:
                    raise
                except Exception as e:  # noqa: BLE001 — fall back to the original audio underneath
                    job.extra["sepError"] = str(getattr(e, "message", None) or e)[:200]
                    return None

            sep_task = asyncio.ensure_future(separate())

        job.phase = "تجهيز النص"
        try:
            plan = await s.live.plan_for(link, o["lang"])
        except AppError as e:
            if e.code != "NO_CAPTIONS":
                raise
            job.phase = "تفريغ الصوت (Whisper)"
            res = await s.whisper.transcribe_file(
                video, lambda p: setattr(job, "progress", 20 + round(p * 15)), lambda: job.cancelled
            )
            cues = [Cue(x["start"], x["end"], x["text"], "") for x in res["segments"]]
            data = VideoCues(
                videoId=job.videoId, title=await s.captions.title(job.videoId), author="", lengthSeconds=0,
                tl=o["lang"], alreadyTranslated=False, asr=True, srcLang=res["lang"] or "", cues=cues,
            )
            plan = Plan(data, False, data.srcLang, group_dub_blocks(cues))
        job.check()
        job.title = (plan.data.title if plan.data else "") or job.videoId
        if not plan.blocks:
            raise AppError("NO_SPEECH", "لا يوجد كلام يمكن دبلجته")
        job.progress = 35

        # Voice: "auto" = male or female from the speaker's pitch; a clear second speaker gets their own.
        voice = o["voice"]
        per_sentence: dict[int, Voice] = {}
        if voice == "auto":
            job.phase = "تحليل أصوات المتحدثين"
            f0s = await _sentence_pitches(job, video, work, plan.blocks)
            split = split_speakers([b.i for b in plan.blocks], f0s)
            voice = split.primary
            job.extra["speakerF0"] = split.median_f0
            if split.per_sentence:
                per_sentence = {i: resolve_voice(g, o["lang"]) for i, g in split.per_sentence.items()}
                job.extra["multiSpeaker"] = True
        v = resolve_voice(voice, o["lang"])

        def voice_of(i: int) -> Voice:
            return per_sentence.get(i) or v

        job.phase = "ترجمة الجمل"
        blocks = await s.live.blocks(plan, 0, math.inf, voice, o["lang"])
        if not blocks:
            raise AppError("TRANSLATE_FAILED", "فشلت الترجمة. أعد المحاولة بعد قليل")
        job.check()
        job.progress = 45

        # Two passes: (a) every sentence at normal speed → its real length; (b) one pace per paragraph
        # from the real lengths → only sentences whose speed changed are made again.
        job.phase = "توليد الصوت المدبلج"
        natural: dict[int, dict] = {}
        concurrency = 4 if v.engine == "edge" else 1
        total = len(blocks) * (2 if v.engine == "edge" else 1)
        done = 0
        fallbacks = 0

        def tick() -> None:
            nonlocal done
            done += 1
            job.progress = 45 + round(done / total * 40)

        async def synth(text: str, voice_: Voice, rate: int, out: Path) -> float:
            nonlocal fallbacks
            dur, fb = await s.tts.synth_wav(text, voice_, rate, out)
            fallbacks += int(fb)
            return dur

        async def natural_one(b: dict) -> None:
            job.check()
            out = work / f"seg_{b['i']:05d}_0.wav"
            try:
                dur = await synth(b["text"], voice_of(b["i"]), 0, out)
                natural[b["i"]] = {"path": out, "duration": dur or s.tts.natural_duration(b["text"], voice_of(b["i"]))}
                s.tts.learn_cps(voice_of(b["i"]), b["text"], 0, dur)
            except Cancelled:
                raise
            except Exception:  # noqa: BLE001 — a sentence without audio is skipped
                pass
            tick()

        await map_limit(blocks, concurrency, natural_one)
        if not natural:
            raise AppError("TTS_FAILED", "تعذّر توليد أي صوت")
        job.check()

        job.phase = "ضبط إيقاع الفقرات"
        paced = pace_blocks(
            [{"i": b["i"], "start": b["srcStart"], "end": b["end"], "text": b["text"]} for b in blocks if b["i"] in natural],
            lambda b: natural[b["i"]]["duration"],
        )
        segs: list[dict] = []

        async def paced_one(p: dict) -> None:
            job.check()
            nat = natural[p["i"]]
            seg = {"i": p["i"], "text": p["text"], "start": p["at"], "slot": p["slot"], "audio": str(nat["path"]),
                   "duration": nat["duration"], "rate": 0}
            if v.engine == "edge" and abs(p["rate"]) >= 3:
                out = work / f"seg_{p['i']:05d}.wav"
                try:
                    seg.update(audio=str(out), duration=await synth(p["text"], voice_of(p["i"]), p["rate"], out), rate=p["rate"])
                except Cancelled:
                    raise
                except Exception:  # noqa: BLE001 — keep the natural-speed clip
                    pass
            segs.append(seg)
            tick()

        await map_limit(paced, concurrency, paced_one)
        segs.sort(key=lambda x: x["start"])
        job.check()

        # Scheduling: each sentence starts on time or when the previous one ends (never two voices).
        # If delay built up and a sentence won't fit, it is made again faster (rare).
        job.phase = "ضبط التوقيت"
        prev_end = 0.0
        refit = 0
        for sg in segs:
            job.check()
            at = max(sg["start"], prev_end + PACE.breath)
            room = max(0.6, sg["start"] + sg["slot"] + DUB_SPILL - at)
            if v.engine == "edge" and sg["duration"] > room * 1.15 and sg["rate"] < 80:
                try:
                    sg["rate"] = fit_rate(sg["rate"], sg["duration"], room)
                    out = work / f"seg_{sg['i']:05d}_fit.wav"
                    sg["duration"] = await synth(sg["text"], voice_of(sg["i"]), sg["rate"], out)
                    sg["audio"] = str(out)
                    refit += 1
                except Cancelled:
                    raise
                except Exception:  # noqa: BLE001
                    pass
            sg["at"] = round(at, 3)
            sg["room"] = round(room, 3)
            prev_end = at + min(sg["duration"], room * 1.25)
        job.progress = 88

        clean_bg = None
        if sep_task:
            job.phase = "إزالة صوت المتحدث الأصلي"
            while not sep_task.done():
                if job.extra.get("sepProgress") is not None:
                    job.phase = f"إزالة صوت المتحدث الأصلي · {job.extra['sepProgress']}%"
                await asyncio.sleep(1)
            clean_bg = sep_task.result()

        job.phase = "دمج الصوت مع الفيديو"
        job.progress = 90
        segs_file = work / "segs.json"
        segs_file.write_text(json.dumps(segs, ensure_ascii=False), encoding="utf-8")
        out_name = f"{safe_name(job.title)}.{o['lang']}.dubbed.mp4"
        mp4 = config.DUBBED / out_name
        args = [
            config.PYTHON, "-m", "tarjuman.media.mixer", "--segments", str(segs_file), "--video", str(video),
            "--wav-out", str(work / "mix.wav"), "--mp4-out", str(mp4),
            "--duration", str(max(b.end for b in plan.blocks) + 1.0), "--bg-volume", str(o["bgVolume"]),
        ]
        if clean_bg:
            args += ["--bg-audio", str(clean_bg)]
        # Pitch matching changes the voice itself; with natural Edge voices picking male/female is enough.
        if v.engine == "piper" and o["matchVoice"]:
            args.append("--match-voice")
        else:
            args += ["--pitch", str(v.pitch if v.engine == "piper" else 1)]
        if o["embedSubs"] or o["burnSubs"]:
            cues = [Cue(c.start, c.end, c.src, c.ar) for c in (plan.data.cues if plan.data else [])]
            if not plan.cues_already_translated:
                await s.translator.translate_cues(cues, tl=o["lang"], sl=plan.src_lang or "auto")
            srt = work / "subs.srt"
            srt.write_text(to_srt(cues, "ar"), encoding="utf-8")
            args += ["--subs", str(srt), "--sub-lang", o["lang"]]
            if o["burnSubs"]:
                job.phase = "دمج الصوت والترجمة في الفيديو"
                args.append("--burn-subs")
        try:
            out = await run_proc(job, args)
        except ProcError as e:
            raise AppError("MIX_FAILED", "فشل الدمج: " + e.stderr[-300:]) from e
        try:
            info = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            info = {}
        job.dubInfo = {
            **info,
            "sentences": len(blocks),
            "refit": refit,
            "voice": v.voice,
            "speakerF0": job.extra.get("speakerF0", 0),
            "multiSpeaker": bool(job.extra.get("multiSpeaker")),
            "voiceRemoved": bool(clean_bg),
            "sepError": job.extra.get("sepError", ""),
            "fallbacks": fallbacks,
        }
        job.progress = 100
        job.phase = "اكتمل"
        job.mp4 = mp4
        job.fileName = out_name
        job.size = mp4.stat().st_size
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------ subtitled MP4


def start_subvideo(s: "Services", link: str, opts: dict) -> str:
    key = _need_key(link)
    _need_python_tools()
    existing = s.jobs.find_active("subvideo", key)
    if existing:
        return existing.id
    job = s.jobs.new(
        "subvideo", key, lang=norm_lang(opts.get("tl")) or "ar", mode="bi" if opts.get("mode") == "bi" else "ar",
        quality=_quality(opts.get("quality")),
    )
    s.jobs.start(job, lambda j: run_subvideo(s, j, link))
    return job.id


async def run_subvideo(s: "Services", job: Job, link: str) -> None:
    """The original audio with the translation burned into the picture."""
    o = job.opts
    work = _fresh_dir(config.TMP / "dub" / f"sub-{work_id(job.videoId)}")
    try:
        job.phase = "تجهيز الترجمة"
        data = await s.captions.get(link, o["lang"])
        job.title = data.title or job.videoId
        cues = [Cue(c.start, c.end, c.src, c.ar) for c in data.cues]
        if not data.alreadyTranslated:
            await s.translator.translate_cues(cues, tl=o["lang"], sl=data.srcLang or "auto")
        (work / "subs.srt").write_text(to_srt(cues, o["mode"]), encoding="utf-8")
        job.progress = 10
        job.check()

        job.phase = "تنزيل الفيديو"
        video = await _download_video(s, job, link, work, o["quality"], 0.4, 10)
        job.check()

        job.phase = "دمج الترجمة في الصورة"
        job.progress = 50
        out_name = f"{safe_name(job.title)}.{o['lang']}.subtitled.mp4"
        mp4 = config.DUBBED / out_name
        total = max(1, data.lengthSeconds or 0)
        from ..media.mixer import BURN_STYLE

        def on_line(line: str) -> None:
            m = re.search(r"out_time_ms=(\d+)", line)
            if m and total > 1:
                job.progress = 50 + min(49, round(int(m.group(1)) / 1e6 / total * 49))

        # ffmpeg runs from the work folder so the subtitle path inside the filter stays simple.
        try:
            await run_proc(
                job,
                [ffmpeg_exe(), "-y", "-loglevel", "error", "-progress", "pipe:1", "-i", str(video),
                 "-vf", f"subtitles=subs.srt:force_style='{BURN_STYLE}'",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                 "-c:a", "copy", "-movflags", "+faststart", str(mp4)],
                cwd=work, on_line=on_line,
            )
        except ProcError as e:
            raise AppError("BURN_FAILED", "فشل دمج الترجمة في الصورة: " + e.stderr[-300:]) from e
        job.progress = 100
        job.phase = "اكتمل"
        job.mp4 = mp4
        job.fileName = out_name
        job.size = mp4.stat().st_size
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------ playlist / channel batch


def start_batch(s: "Services", link: str, opts: dict) -> str:
    _need_python_tools()
    if not re.match(r"^https?://", str(link), re.I):
        raise AppError("BAD_URL")
    what = opts.get("what") if opts.get("what") in ("subs", "subvideo", "dub") else "subs"
    try:
        limit = min(200, max(1, int(opts.get("limit") or 50)))
    except (TypeError, ValueError):
        limit = 50
    job = s.jobs.new(
        "batch", "batch", link=link, what=what, lang=norm_lang(opts.get("tl")) or "ar", limit=limit,
        voice=opts.get("voice") or "auto", quality=_quality(opts.get("quality")), bgVolume=opts.get("bgVolume"),
        embedSubs=opts.get("embedSubs") is not False,
    )
    s.jobs.start(job, lambda j: run_batch(s, j))
    return job.id


async def run_batch(s: "Services", job: Job) -> None:
    o = job.opts
    job.phase = "قراءة القائمة"
    title, entries = await ytdlp.list_playlist(job, o["link"], o["limit"])
    if not entries:
        raise AppError("PLAYLIST_EMPTY", "القائمة فارغة أو ليست قائمة تشغيل")
    job.title = title or "قائمة تشغيل"
    items = job.extra["items"] = [{**e, "status": "queued", "message": ""} for e in entries]

    for k, item in enumerate(items):
        job.check()
        link = "https://www.youtube.com/watch?v=" + item["id"]
        job.phase = f"فيديو {k + 1} من {len(items)}: {item['title']}"
        item["status"] = "running"
        try:
            if o["what"] == "subs":
                data = await s.captions.get(link, o["lang"])
                if not data.alreadyTranslated:
                    await s.translator.translate_cues(data.cues, tl=o["lang"], sl=data.srcLang or "auto")
                base = safe_name(data.title)
                (config.OUTPUT / f"{base}.{o['lang']}.srt").write_text("﻿" + to_srt(data.cues, "ar"), encoding="utf-8")
                (config.OUTPUT / f"{base}.bilingual.srt").write_text("﻿" + to_srt(data.cues, "bi"), encoding="utf-8")
            else:
                # Each video is its own job (it shows in "My files" and can be cancelled); the batch waits for it.
                if o["what"] == "dub":
                    sub = s.jobs.new("dub", item["id"], **dub_options({
                        "lang": o["lang"], "voice": o["voice"], "quality": o["quality"], "bgVolume": o["bgVolume"],
                        "embedSubs": o["embedSubs"],
                    }))
                else:
                    sub = s.jobs.new("subvideo", item["id"], lang=o["lang"], mode="ar", quality=o["quality"])
                job.current = sub
                sub.phase = "في انتظار انتهاء مهمة أخرى"
                async with s.jobs.slot(sub.type):
                    sub.status = "running"
                    await (run_dub(s, sub, link) if o["what"] == "dub" else run_subvideo(s, sub, link))
                sub.status = "done"
            item["status"] = "done"
        except Exception as e:  # noqa: BLE001
            if job.cancelled:
                raise
            if job.current and job.current.status == "running":
                job.current.status = "error"
                job.current.message = str(getattr(e, "message", None) or e)[:300]
            item["status"] = "error"
            item["message"] = "لا توجد له ترجمة" if getattr(e, "code", "") == "NO_CAPTIONS" else str(getattr(e, "message", None) or e)[:160]
        finally:
            job.current = None
        job.progress = round((k + 1) / len(items) * 100)
    failed = sum(1 for x in items if x["status"] == "error")
    job.phase = f"اكتمل، وتعذّر إنجاز {failed} من الفيديوهات" if failed else "اكتمل"


# ------------------------------------------------------------------ download from any site


def start_fetch(s: "Services", link: str) -> str:
    _need_python_tools()
    if not re.match(r"^https?://", link, re.I):
        raise AppError("BAD_URL")
    job = s.jobs.new("fetch", "fetch-" + hashlib.sha1(link.encode()).hexdigest()[:10], link=link)
    s.jobs.start(job, lambda j: run_fetch(s, j, link))
    return job.id


async def run_fetch(s: "Services", job: Job, link: str) -> None:
    job.phase = "تنزيل الفيديو"
    item = s.media.new_item("video", "mp4", link)
    try:
        file, title = await ytdlp.fetch_any(job, link, s.media.folder, item.id, lambda p: setattr(job, "progress", round(p)))
    except BaseException:
        s.media.items.pop(item.id, None)
        raise
    item.file = file.name
    item.title = safe_name(title) or item.id
    item.size = file.stat().st_size
    s.media.save()
    job.title = item.title
    job.extra["media"] = item.public()
    job.progress = 100
    job.phase = "اكتمل"


