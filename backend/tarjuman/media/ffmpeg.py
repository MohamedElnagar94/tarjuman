"""The bundled ffmpeg (imageio-ffmpeg ships one with libass, harfbuzz, fribidi and x264)."""

from __future__ import annotations

from functools import lru_cache

from ..core.errors import AppError


@lru_cache(maxsize=1)
def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # noqa: BLE001
        raise AppError("FFMPEG_NOT_FOUND", str(e)) from e


def available() -> bool:
    try:
        ffmpeg_exe()
        return True
    except AppError:
        return False
