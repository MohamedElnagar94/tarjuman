"""Everything the API needs, wired together once."""

from __future__ import annotations

from . import config
from .ai.client import AiClient
from .ai.insights import Insights
from .ai.script import ScriptWriter
from .ai.settings import AiSettings
from .asr import Whisper
from .captions.service import CaptionService
from .dub.live import LivePlanner
from .jobs.manager import JobManager
from .learn.vocab import Vocab
from .media.library import MediaLibrary
from .translate.service import Translator
from .voice.pronounce import PronunciationDict
from .voice.service import TtsService


class Services:
    def __init__(self) -> None:
        config.ensure_dirs()
        c = config.CACHE
        self.media = MediaLibrary(config.MEDIA_DIR)
        self.captions = CaptionService(self.media)
        self.translator = Translator(c / "translations.json", c / "edits.json")
        self.pronounce = PronunciationDict(config.DATA / "pronounce.json")
        self.tts = TtsService(config.TTS_DIR, config.PIPER_MODEL, self.pronounce)
        self.ai = AiSettings(config.DATA / "settings.json")
        self.ai_client = AiClient(self.ai)
        self.writer = ScriptWriter(self.ai, self.ai_client, c / "ai-script.json")
        self.insights = Insights(self.ai, self.ai_client)
        self.live = LivePlanner(self.captions, self.translator, self.tts, self.writer, self.ai)
        self.whisper = Whisper(config.WHISPER_MODEL, config.TMP)
        self.jobs = JobManager()
        self.vocab = Vocab(config.DATA / "vocab.json")

    def load(self) -> None:
        for part in (self.media, self.translator, self.pronounce, self.tts, self.ai, self.writer, self.vocab):
            part.load()

    def flush(self) -> None:
        for part in (self.translator, self.tts, self.writer):
            part.flush()
