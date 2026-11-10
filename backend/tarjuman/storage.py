"""What the app keeps on disk, how big it is, and how to keep it in check."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from . import config

if TYPE_CHECKING:
    from .services import Services

CLIP_EXT = (".mp3", ".wav")


def folder_size(path: Path, *, top_only: bool = False) -> tuple[int, int]:
    """(bytes, files) under ``path``. ``top_only`` skips subfolders."""
    total = count = 0
    if not path.exists():
        return 0, 0
    walker = [(str(path), [], [e.name for e in os.scandir(path) if e.is_file()])] if top_only else os.walk(path)
    for root, _dirs, files in walker:
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
                count += 1
            except OSError:
                pass
    return total, count


def usage() -> dict[str, dict[str, int]]:
    def entry(size_count: tuple[int, int]) -> dict[str, int]:
        return {"bytes": size_count[0], "files": size_count[1]}

    translations = sum(
        (config.CACHE / f).stat().st_size for f in ("translations.json", "ai-script.json") if (config.CACHE / f).exists()
    )
    return {
        "voices": entry(folder_size(config.TTS_DIR)),
        "translations": {"bytes": translations, "files": 0},
        "dubbed": entry(folder_size(config.DUBBED)),
        "subtitles": entry(folder_size(config.OUTPUT, top_only=True)),
        "media": entry(folder_size(config.MEDIA_DIR)),
        "models": entry(folder_size(config.MODELS)),
        "tmp": entry(folder_size(config.TMP)),
    }


def prune_clips(folder: Path, limit: int, meta: dict[str, float] | None = None) -> int:
    """Delete the least recently used voice clips until the folder is under 90% of ``limit``.
    A clip's modification time is refreshed whenever it is played, so it marks its last use.
    Returns the number of clips deleted."""
    clips = []
    total = 0
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return 0
    for e in entries:
        if e.is_file() and e.name.endswith(CLIP_EXT):
            st = e.stat()
            clips.append((st.st_mtime, st.st_size, e.path, e.name))
            total += st.st_size
    if total <= limit:
        return 0
    clips.sort()
    target = limit * 0.9
    deleted = 0
    for _mtime, size, path, name in clips:
        if total <= target:
            break
        try:
            os.unlink(path)
        except OSError:
            continue
        total -= size
        deleted += 1
        if meta is not None:
            meta.pop(name.rsplit(".", 1)[0], None)
    return deleted


def clear_tmp() -> None:
    """Work folders of jobs. Called when no job is running (at startup, or on request)."""
    if config.TMP.exists():
        for e in os.scandir(config.TMP):
            try:
                shutil.rmtree(e.path) if e.is_dir() else os.unlink(e.path)
            except OSError:
                pass


def clear(s: "Services", what: str) -> None:
    if what == "voices":
        for e in os.scandir(config.TTS_DIR):
            if e.is_file() and e.name.endswith(CLIP_EXT):
                try:
                    os.unlink(e.path)
                except OSError:
                    pass
        s.tts.meta.clear()
        s.live.natural.clear()
    elif what == "translations":
        # The user's own corrections (edits.json) are kept: they are work, not cache.
        s.translator.cache.clear()
        (config.CACHE / "translations.json").unlink(missing_ok=True)
        s.writer.cache.clear()
        (config.CACHE / "ai-script.json").unlink(missing_ok=True)
        s.live.reset_texts()
    elif what == "tmp":
        if s.jobs.running_count():
            from .core.errors import AppError

            raise AppError("JOBS_RUNNING", "توجد مهام قيد التشغيل تستخدم الملفات المؤقتة. انتظر انتهاءها.")
        clear_tmp()
