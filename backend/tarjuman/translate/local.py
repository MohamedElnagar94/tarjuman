"""Translation on this computer, without the internet: the University of Helsinki's OPUS-MT models.

Each language pair is downloaded once from its official release (a Marian model), converted on this
computer to CTranslate2 int8 (the same engine as Whisper; numpy and yaml only, no PyTorch) and kept in
data/models/opus/<src>-<tgt>. English to 42 languages and 44 languages to English exist; other pairs go
through English (Chinese -> English -> Arabic).

Measured on a TED talk (14 Nov 2026): about 17 lines a second on a 2016 laptop CPU, with more meaning
errors than Google Translate (about 10 in 50 lines against 3). So it is the fallback when the online
translators refuse, or the choice of someone who wants nothing to leave the computer."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import threading
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any

from ..core import http
from ..core.errors import AppError
from ..core.langs import ISO3
from ..core.store import read_json, write_json

log = logging.getLogger("tarjuman.mt")

PAIRS: dict[str, str] = json.loads(Path(__file__).with_name("opus_models.json").read_text(encoding="utf-8"))["pairs"]
KEEP_LOADED = 2
PREFS = ("online", "offline")

# Language tags some models need in front of the text (">>ara<<"); the first one the model knows wins.
TAG_CODES = {"zh": ["cmn_Hans", "zho_Hans", "cmn", "zho"], "pt": ["por"], "nb": ["nob", "nor"], "ms": ["zsm_Latn", "msa"]}


def _latin(texts: list[str]) -> bool:
    """Mostly Latin letters: an unknown source language is taken to be English."""
    letters = "".join(re.findall(r"[^\W\d_]", " ".join(texts)))
    return bool(letters) and sum(1 for ch in letters if ch < "ɏ") / len(letters) > 0.9


class LocalMT:
    def __init__(self, folder: Path, settings_file: Path):
        self.dir = folder
        self.settings_file = settings_file
        self.prefer = "online"
        self._models: OrderedDict[str, tuple[Any, Any, Any, str]] = OrderedDict()
        self._lock = threading.Lock()
        # Downloads in progress or failed: pair -> {status, progress, phase, error}
        self.installs: dict[str, dict] = {}

    def load(self) -> None:
        p = read_json(self.settings_file, {}).get("prefer")
        self.prefer = p if p in PREFS else "online"

    def set_prefer(self, prefer: str) -> None:
        if prefer not in PREFS:
            raise AppError("BAD_REQUEST")
        self.prefer = prefer
        write_json(self.settings_file, {"prefer": prefer})

    # ---------------- what is here ----------------

    def path(self, pair: str) -> Path:
        return self.dir / pair

    def installed(self, pair: str) -> bool:
        p = self.path(pair)
        return (p / "model.bin").exists() and (p / "source.spm").exists() and (p / "target.spm").exists()

    def installed_pairs(self) -> list[str]:
        return sorted(p.name for p in self.dir.glob("*-*") if self.installed(p.name)) if self.dir.exists() else []

    def route(self, sl: str, tl: str, texts: list[str] | None = None) -> list[str] | None:
        """The installed models that take ``sl`` to ``tl``: one pair, or two through English."""
        if sl in ("", "auto"):
            if not texts or not _latin(texts):
                return None
            sl = "en"
        if sl == tl:
            return None
        if self.installed(f"{sl}-{tl}"):
            return [f"{sl}-{tl}"]
        if sl != "en" and tl != "en" and self.installed(f"{sl}-en") and self.installed(f"en-{tl}"):
            return [f"{sl}-en", f"en-{tl}"]
        return None

    def status(self) -> dict:
        size = {p: sum(f.stat().st_size for f in self.path(p).glob("*") if f.is_file()) for p in self.installed_pairs()}
        return {
            "prefer": self.prefer,
            "installed": self.installed_pairs(),
            "bytes": size,
            "available": sorted(PAIRS),
            "installs": self.installs,
        }

    # ---------------- download and convert ----------------

    def install(self, pair: str) -> None:
        if pair not in PAIRS:
            raise AppError("NOT_FOUND")
        if self.installed(pair) or (self.installs.get(pair) or {}).get("status") == "working":
            return
        self.installs[pair] = {"status": "working", "progress": 0, "phase": "download", "error": ""}
        asyncio.ensure_future(self._install(pair))

    async def _install(self, pair: str) -> None:
        st = self.installs[pair]
        work = self.dir / f".{pair}.work"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        try:
            zpath = work / "model.zip"
            await self._download(PAIRS[pair], zpath, st)
            st.update(phase="convert", progress=95)
            await asyncio.to_thread(self._convert, zpath, work, self.path(pair))
            st.update(status="done", progress=100, phase="")
            self.installs.pop(pair, None)
        except Exception as e:  # noqa: BLE001 — reported to the settings page
            log.warning("offline translation model %s failed: %r", pair, e)
            st.update(status="error", error=getattr(e, "code", "") or "DOWNLOAD_FAILED")
        finally:
            shutil.rmtree(work, ignore_errors=True)

    async def _download(self, url: str, dest: Path, st: dict) -> None:
        async with http.client().stream("GET", url, timeout=600) as res:
            if res.status_code >= 400:
                raise AppError("DOWNLOAD_FAILED")
            total = int(res.headers.get("content-length") or 0)
            got = 0
            with open(dest, "wb") as fh:
                async for chunk in res.aiter_bytes(1 << 17):
                    fh.write(chunk)
                    got += len(chunk)
                    if total:
                        st["progress"] = min(94, round(got / total * 94))

    def _convert(self, zpath: Path, work: Path, out: Path) -> None:
        import ctranslate2

        src = work / "marian"
        with zipfile.ZipFile(zpath) as z:
            for n in z.namelist():
                if n.endswith((".npz", ".yml", ".spm")) and "/" not in n.strip("/"):
                    z.extract(n, src)
        zpath.unlink(missing_ok=True)
        tmp = work / "ct2"
        ctranslate2.converters.OpusMTConverter(str(src)).convert(str(tmp), quantization="int8", force=True)
        for spm in ("source.spm", "target.spm"):
            shutil.copy(src / spm, tmp / spm)
        shutil.rmtree(out, ignore_errors=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp), str(out))

    def delete(self, pair: str) -> None:
        with self._lock:
            self._models.pop(pair, None)
        shutil.rmtree(self.path(pair), ignore_errors=True)
        self.installs.pop(pair, None)

    # ---------------- translate ----------------

    def _model(self, pair: str, tl: str):
        with self._lock:
            hit = self._models.get(pair)
            if hit:
                self._models.move_to_end(pair)
                return hit
        import ctranslate2
        import sentencepiece as spm

        p = self.path(pair)
        tr = ctranslate2.Translator(str(p), device="cpu", compute_type="int8", intra_threads=4)
        vocab = json.loads((p / "shared_vocabulary.json").read_text(encoding="utf-8")) if (p / "shared_vocabulary.json").exists() else []
        tags = {t[2:-2] for t in vocab if re.fullmatch(r">>[\w-]+<<", t)}
        tag = ""
        if tags:
            want = [*TAG_CODES.get(tl, []), ISO3.get(tl, tl)]
            tag = next((f">>{c}<<" for c in want if c in tags), "")
        entry = (tr, spm.SentencePieceProcessor(model_file=str(p / "source.spm")), spm.SentencePieceProcessor(model_file=str(p / "target.spm")), tag)
        with self._lock:
            self._models[pair] = entry
            while len(self._models) > KEEP_LOADED:
                self._models.popitem(last=False)
        return entry

    def _run(self, pair: str, tl: str, texts: list[str]) -> list[str]:
        tr, sp_src, sp_tgt, tag = self._model(pair, tl)
        batch = [([tag] if tag else []) + sp_src.encode(t, out_type=str)[:400] for t in texts]
        res = tr.translate_batch(batch, beam_size=4, max_batch_size=16, max_decoding_length=512)
        return [sp_tgt.decode(r.hypotheses[0]).strip() for r in res]

    async def translate(self, texts: list[str], sl: str, tl: str) -> list[str] | None:
        """Translations in order, or None when no installed model takes sl to tl."""
        route = self.route(sl, tl, texts)
        if not route or not texts:
            return None
        out = texts
        for i, pair in enumerate(route):
            out = await asyncio.to_thread(self._run, pair, tl if i == len(route) - 1 else "en", out)
        return out
