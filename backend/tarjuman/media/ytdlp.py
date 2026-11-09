"""yt-dlp as a subprocess (so a cancel can kill it), with progress parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from .. import config
from ..core.errors import AppError, Cancelled
from ..jobs.manager import Job, ProcError, run_proc
from .ffmpeg import ffmpeg_exe

_PROGRESS = re.compile(r"\[download\]\s+([\d.]+)%")


def mp4_format(height: int) -> str:
    return f"bv*[vcodec^=avc1][height<={height}]+ba[ext=m4a]/b[ext=mp4][height<={height}]/bv*[height<={height}]+ba/b"


def is_final(name: str) -> bool:
    return not re.search(r"\.(part|ytdl|temp)$", name, re.I) and not re.search(r"\.f\d+\.", name)


def _tail(e: ProcError, lines: int = 1) -> str:
    return " ".join(str(e.stderr).strip().splitlines()[-lines:])


async def download(
    job: Job,
    link: str,
    out_dir: Path,
    base: str,
    fmt: str,
    *,
    merge_mp4: bool = False,
    on_progress: Callable[[float], None] | None = None,
) -> Path:
    args = [config.PYTHON, "-m", "yt_dlp", "-f", fmt, "--no-playlist", "--no-warnings", "--newline"]
    if merge_mp4:
        args += ["--merge-output-format", "mp4", "--ffmpeg-location", ffmpeg_exe()]
    args += ["-o", str(out_dir / f"{base}.%(ext)s"), link]

    def on_line(s: str) -> None:
        m = _PROGRESS.search(s)
        if m and on_progress:
            on_progress(float(m.group(1)))

    try:
        await run_proc(job, args, on_line=on_line)
    except ProcError as e:
        raise AppError("YTDLP_FAILED", "yt-dlp: " + _tail(e, 3)[-300:]) from e
    files = sorted(f.name for f in out_dir.iterdir() if f.name.startswith(base + ".") and is_final(f.name))
    if not files:
        raise AppError("DOWNLOAD_FAILED")
    return out_dir / (f"{base}.mp4" if f"{base}.mp4" in files else files[0])


async def fetch_any(job: Job, link: str, out_dir: Path, base: str, on_progress: Callable[[float], None]) -> tuple[Path, str]:
    """Download a video from any site yt-dlp supports (Vimeo, Facebook, TikTok…). Returns (file, title)."""
    args = [
        config.PYTHON, "-m", "yt_dlp", "--no-playlist", "--no-warnings", "--newline", "--no-simulate",
        "--print", "title", "-f", "bv*[height<=720]+ba/b[height<=720]/b", "--merge-output-format", "mp4",
        "--ffmpeg-location", ffmpeg_exe(), "-o", str(out_dir / f"{base}.%(ext)s"), link,
    ]

    def on_line(s: str) -> None:
        m = _PROGRESS.search(s)
        if m:
            on_progress(float(m.group(1)))

    try:
        out = await run_proc(job, args, on_line=on_line)
    except Cancelled:
        raise
    except ProcError as e:
        raise AppError("YTDLP_FAILED", "مقدرتش أنزّل الفيديو من اللينك ده: " + _tail(e)[:200]) from e
    title = next((x.strip() for x in out.splitlines() if x.strip() and not x.strip().startswith("[")), "")
    files = [f for f in out_dir.iterdir() if f.name.startswith(base + ".") and is_final(f.name)]
    if not files:
        raise AppError("DOWNLOAD_FAILED")
    return files[0], title


async def list_playlist(job: Job, link: str, limit: int) -> tuple[str, list[dict]]:
    """A playlist's or channel's videos, without downloading anything."""
    args = [config.PYTHON, "-m", "yt_dlp", "--flat-playlist", "-J", "--no-warnings", "--playlist-end", str(limit), link]
    try:
        out = await run_proc(job, args)
    except ProcError as e:
        raise AppError("PLAYLIST_FAILED", "مقدرتش أقرا القايمة: " + _tail(e)[:200]) from e
    j = json.loads(out)
    entries = [
        {"id": e.get("id"), "title": e.get("title") or e.get("id")}
        for e in (j.get("entries") or [j])
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", str(e.get("id") or ""))
    ]
    return j.get("title") or "", entries[:limit]
