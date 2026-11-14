"""A Tarjuman server for browser tests: real app, real web build, no internet.

Translation and voices are fakes, the data folder is a fresh temporary one, and the library holds
one short video that already has a transcript (so nothing needs YouTube or Whisper).

    python tests/e2e_server.py [port]
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

os.environ["TARJUMAN_NO_ENV_FILE"] = "1"
os.environ["TARJUMAN_HOME"] = tempfile.mkdtemp(prefix="tarjuman-e2e-")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from tarjuman.api.app import create_app  # noqa: E402
from tarjuman.media.ffmpeg import ffmpeg_exe  # noqa: E402
from tarjuman.services import Services  # noqa: E402
from tarjuman.voice.service import TtsResult  # noqa: E402

SEGMENTS = [
    {"start": 0.5, "end": 2.5, "text": "Hello and welcome to this short lesson."},
    {"start": 3.0, "end": 5.5, "text": "Today we talk about large language models."},
    {"start": 6.0, "end": 8.5, "text": "Thank you for watching."},
]
ARABIC = {
    SEGMENTS[0]["text"]: "مرحبًا بكم في هذا الدرس القصير.",
    SEGMENTS[1]["text"]: "نتحدث اليوم عن النماذج اللغوية الكبيرة.",
    SEGMENTS[2]["text"]: "شكرًا لكم على المشاهدة.",
}


# A 30-second voice note with three sentences, and one with no transcript yet.
VOICE = [
    {"start": 1.0, "end": 6.0, "text": "This is the start of my voice note."},
    {"start": 12.0, "end": 18.0, "text": "Here is the middle part."},
    {"start": 23.0, "end": 28.0, "text": "And this is the end."},
]
# What the fake AI summary suggests for the voice note: three chapters.
VOICE_CHAPTERS = [{"start": 0, "title": "البداية"}, {"start": 11, "title": "الوسط"}, {"start": 22, "title": "النهاية"}]


def silence(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * int(16000 * seconds))
    return buf.getvalue()


def make_services() -> Services:
    s = Services()

    async def translate_many(texts, sl="auto", tl="ar", **_):
        return {t: ARABIC.get(t, "ترجمة: " + t) for t in texts if t}

    async def speak(text, lang="ar", voice="", rate=0, *, priority=2):
        seconds = max(0.4, round(len(text) / 14 / (1 + float(rate) / 100), 3))
        return TtsResult(silence(seconds), "audio/wav", seconds, "edge")

    s.translator.translate_many = translate_many
    s.tts.speak = speak

    item = s.media.new_item("Short lesson", "mp4", "upload")
    subprocess.run(
        [
            ffmpeg_exe(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=9:size=320x180:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=330:duration=9", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(item.path),
        ],
        check=True,
    )
    item.size = item.path.stat().st_size
    item.segments, item.lang, item.duration = SEGMENTS, "en", 9.0

    for title, segments in (("Voice note", VOICE), ("Silent memo", [])):
        note = s.media.new_item(title, "m4a", "upload")
        subprocess.run(
            [ffmpeg_exe(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=30", "-c:a", "aac", str(note.path)],
            check=True,
        )
        note.size = note.path.stat().st_size
        note.duration, note.kind = 30.0, "audio"
        if segments:
            note.segments, note.lang = segments, "en"
    s.media.save()

    # The AI isn't set up in tests; its summary is a fixed one so the chapters it suggests can be checked.
    async def summary(data, tl):
        return {"summary": "ملخص قصير.", "points": ["نقطة"], "chapters": VOICE_CHAPTERS if data.title == "Voice note" else []}

    s.insights.summary = summary
    return s


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4390
    app = create_app(make_services(), port=port, warm=False)
    print(f"e2e server on http://127.0.0.1:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
