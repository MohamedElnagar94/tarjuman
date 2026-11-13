"""Speech-to-text settings (Settings -> Transcription), and what this computer can run.

Accuracy depends mostly on the Whisper model: the bigger, the better (Arabic gains the most), and the
slower. What fits depends on the computer, so the app looks at it (cores, memory, an NVIDIA card and
whether CUDA can use it) and recommends a model with its reasons. "auto" follows that recommendation;
any choice the user makes wins, and the page shows why each option is or isn't advised.

Kept in data/asr.json. TARJUMAN_WHISPER_MODEL (.env) still picks the model while this is "auto".
"""

from __future__ import annotations

import ctypes
import logging
import os
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from .core.store import read_json, write_json

log = logging.getLogger("tarjuman.asr")

# size: download (MB); ram: memory it needs on the CPU (GB); spm: seconds per minute of audio on an
# 8-thread CPU (int8, beam 5, word times), measured on Arabic speech; ar: Arabic accuracy, 1-5.
MODELS: dict[str, dict[str, Any]] = {
    "tiny": {"size": 75, "ram": 0.5, "spm": 8, "ar": 1},
    "base": {"size": 145, "ram": 0.7, "spm": 15, "ar": 2},
    "small": {"size": 484, "ram": 1.2, "spm": 36, "ar": 3},
    "medium": {"size": 1530, "ram": 2.6, "spm": 150, "ar": 4},
    "large-v3-turbo": {"size": 1620, "ram": 2.8, "spm": 115, "ar": 4},
    "large-v3": {"size": 3100, "ram": 4.8, "spm": 190, "ar": 4},
    # Whisper large-v3 fine-tuned on Arabic dialects (Egyptian, Gulf, Levantine, Maghrebi, MSA). For
    # Arabic speech only. On a real 36 s Egyptian voice note it got 29% of the words wrong without the
    # words list and 24% with it, against 41% and 29% for large-v3.
    "large-v3-arabic": {"size": 3090, "ram": 4.8, "spm": 170, "ar": 5, "arabicOnly": True},
}
# Models not in faster-whisper's own list: where they are downloaded from, pinned to a known version.
REPOS: dict[str, tuple[str, str]] = {
    # Apache-2.0: oddadmix/whisper-large-v3-arabic-dialectal-v2, converted for CTranslate2.
    "large-v3-arabic": ("SohailElsek/whisper-large-v3-arabic-dialectal-v2-ct2", "ae3724b6c083d793f70c68c290a749a1a1b0d06c"),
}
# In "auto" on a CPU, a recording up to this long gets the most accurate model the computer can hold,
# whatever its speed: a voice note is worth the wait. Longer ones get the recommended model.
# Measured on a 36 s Egyptian voice note with names and English words: large-v3 got 29% of the words
# wrong, large-v3-turbo 45-50% (and turbo ignores the names list), at a third of the time.
SHORT_SECONDS = 120
# On a GPU everything is ~10-20x faster.
GPU_SPEEDUP = 12

STYLES = ("general", "msa", "egyptian", "gulf", "levantine", "maghrebi", "none")
# Whisper continues the style of the text it is given before the audio: an Arabic sentence with
# punctuation keeps it writing Arabic script, with punctuation, in the same register. Used only when
# the speech is Arabic (forced, or detected first), never to push another language into Arabic.
PROMPTS = {
    "general": "هذا تسجيل باللغة العربية، مكتوب بإملاء صحيح وعلامات ترقيم واضحة.",
    "msa": "نصٌّ عربيٌّ فصيح، مكتوبٌ بعناية، مع علامات الترقيم: الفاصلة، والنقطة، وعلامة الاستفهام؟",
    "egyptian": "ده تسجيل بالعامية المصرية، وبنكتب الكلام زي ما اتقال بالظبط، يعني إزاي وليه وعايز إيه.",
    "gulf": "هذا تسجيل باللهجة الخليجية، نكتب الكلام مثل ما انقال: شلونك، زين، وايد، الحين.",
    "levantine": "هاد تسجيل باللهجة الشامية، منكتب الحكي متل ما انقال: كيفك، منيح، هلق، شو بدك.",
    "maghrebi": "هادا تسجيل بالدارجة المغاربية، كنكتبو الهضرة كيف تقالت: واش، بزاف، دابا، مزيان.",
}
# Languages offered on the page; any language Whisper knows is accepted.
LANGS = ("auto", "ar", "en", "fr", "es", "de", "tr", "ur", "fa", "hi", "id", "ru", "zh", "ja", "ko", "it", "pt")

DEFAULTS: dict[str, Any] = {
    "model": "auto",  # or one of MODELS
    "device": "auto",  # auto | cpu | cuda
    "language": "auto",  # auto | a language code
    "style": "general",  # how Arabic is written (STYLES)
    "quality": "accurate",  # accurate (beam search 5) | fast (greedy)
    "enhance": False,  # clean the audio first (noise, hum, level)
    "vad": True,  # skip long silences (fewer invented sentences)
    # Names and words that come up in the user's recordings (people, places, brands), as rows
    # {"from": what Whisper writes (optional), "to": how it should be written}. Whisper is told every
    # "to" before transcribing, and any "from" left in the text is replaced by its "to" afterwards.
    "terms": [],
    # Have the AI (Settings -> AI, when set up) fix words Whisper clearly misheard, from the context.
    "aiFix": False,
}
TERMS_MAX = 80
TERM_LEN = 60


def _ram_gb() -> float:
    try:
        import psutil  # type: ignore

        return psutil.virtual_memory().total / 2**30
    except Exception:  # noqa: BLE001
        pass
    if sys.platform == "win32":

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                (n, ctypes.c_ulonglong)
                for n in ("total", "avail", "pagefile", "availPage", "virtual", "availVirtual", "availExt")
            ]

        s = MEMORYSTATUSEX()
        s.dwLength = ctypes.sizeof(s)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
            return s.total / 2**30
        return 0.0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (ValueError, OSError, AttributeError):
        return 0.0


def _physical_cores() -> int:
    try:
        import psutil  # type: ignore

        return int(psutil.cpu_count(logical=False) or 0)
    except Exception:  # noqa: BLE001
        return 0


def _gpu_name() -> tuple[str, float, float]:
    """(name, memory in GB, CUDA compute capability) of the first NVIDIA card."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return "", 0.0, 0.0
    try:
        out = subprocess.run(
            [exe, "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout.strip().splitlines()
        name, mem, cap = ([x.strip() for x in out[0].split(",")] + ["0", "0"])[:3]
        try:
            cc = float(cap)
        except ValueError:
            cc = 0.0
        return name, round(float(mem) / 1024, 1), cc
    except Exception:  # noqa: BLE001
        return "", 0.0, 0.0


# Cards before Pascal (compute capability 6.0: GTX 10xx, Quadro P) have neither fast half precision nor
# int8 for these models: even with CUDA installed the gain over the CPU is small or none.
MODERN_GPU = 6.0


def _cuda_devices() -> int:
    try:
        import ctranslate2  # type: ignore

        return int(ctranslate2.get_cuda_device_count())
    except Exception:  # noqa: BLE001
        return 0


def _cublas_found() -> bool:
    """CTranslate2 needs NVIDIA's cuBLAS 12 to run on the card (cuDNN comes with it on Windows). It is
    part of the CUDA toolkit, not of the graphics driver."""
    names = ("cublas64_12.dll", "cublasLt64_12.dll") if sys.platform == "win32" else ("libcublas.so.12", "libcublasLt.so.12")
    for n in names:
        try:
            (ctypes.WinDLL if sys.platform == "win32" else ctypes.CDLL)(n)  # type: ignore[attr-defined]
        except OSError:
            return False
    return True


@lru_cache(maxsize=1)
def hardware() -> dict[str, Any]:
    cuda = _cuda_devices()
    gpu, vram, cc = _gpu_name() if cuda else ("", 0.0, 0.0)
    return {
        "os": {"win32": "windows", "darwin": "mac"}.get(sys.platform, "linux"),
        "threads": os.cpu_count() or 1,
        "cores": _physical_cores(),
        "ramGb": round(_ram_gb(), 1),
        "cuda": cuda,  # NVIDIA cards the driver reports
        "gpu": gpu,
        "vramGb": vram,
        "computeCap": cc,
        # An old card: CUDA could run on it, but not usefully faster than the CPU.
        "gpuOld": bool(cuda) and 0 < cc < MODERN_GPU,
        "cublas": bool(cuda) and _cublas_found(),
    }


def gpu_usable(hw: dict[str, Any], allow_old: bool = False) -> bool:
    """Whether transcription can run on the card. An old card is used only when asked for."""
    return bool(hw.get("cuda")) and bool(hw.get("cublas")) and (allow_old or not hw.get("gpuOld"))


def cpu_threads(hw: dict[str, Any]) -> int:
    return max(1, min(16, int(hw.get("threads") or 1)))


def seconds_per_minute(model: str, hw: dict[str, Any], device: str) -> int:
    spm = MODELS[model]["spm"] * 8 / cpu_threads(hw)
    if device == "cuda":
        spm /= GPU_SPEEDUP
    return max(1, round(spm))


def recommend(hw: dict[str, Any], arabic: bool = False) -> dict[str, Any]:
    """The model this computer should use, and why, in plain words (Arabic; the page shows them).
    ``arabic``: the spoken language is set to Arabic, so the Arabic-dialect model can be used."""
    rec = _recommend(hw)
    if arabic and rec.get("short") == "large-v3":
        rec["short"] = "large-v3-arabic"
        rec["why"].append(
            "ولأنك اخترت العربية لغةً للكلام، تُفرَّغ التسجيلات القصيرة بنموذج large-v3-arabic، وهو large-v3 مدرَّب على "
            "اللهجات العربية: كان الأدق في تجربتنا على رسالة صوتية بالعامية المصرية."
        )
    elif not arabic and rec.get("short") == "large-v3" and float(hw.get("ramGb") or 0) >= 12:
        rec["why"].append("إن كانت تسجيلاتك عربية دائمًا فاختر العربية في «لغة الكلام»: يُستعمل حينها نموذج مدرَّب على اللهجات العربية، أدق للعامية.")
    return rec


def _recommend(hw: dict[str, Any]) -> dict[str, Any]:
    why: list[str] = []
    ram, threads = float(hw.get("ramGb") or 0), int(hw.get("threads") or 1)
    card = f" ({hw['gpu']})" if hw.get("gpu") else ""
    vram = float(hw.get("vramGb") or 0)
    if gpu_usable(hw) and (not vram or vram >= 6):
        why.append(f"لديك بطاقة رسوميات NVIDIA{card} تعمل مع CUDA وذاكرتها كافية، فيعمل أدقّ نموذج (large-v3) بسرعة كبيرة.")
        return {"model": "large-v3", "device": "cuda", "short": "large-v3", "why": why}
    if gpu_usable(hw) and vram >= 3:
        why.append(f"لديك بطاقة رسوميات NVIDIA{card} تعمل مع CUDA، وذاكرتها {vram:g} غيغابايت تكفي لنموذج large-v3-turbo.")
        return {"model": "large-v3-turbo", "device": "cuda", "short": "large-v3-turbo", "why": why}
    if hw.get("gpuOld"):
        why.append(
            f"بطاقة الرسوميات{card} من جيل قديم (قدرة CUDA {hw.get('computeCap'):g})، لا تدعم طرق الحساب السريعة التي "
            "تستعملها هذه النماذج، فالفائدة منها قليلة أو معدومة حتى لو ثبّتّ CUDA. يعمل التفريغ على المعالج، ولا تحتاج تثبيت شيء."
        )
    elif gpu_usable(hw):
        why.append(f"بطاقة الرسوميات{card} ذاكرتها {vram:g} غيغابايت فقط، لا تكفي النماذج الدقيقة، فيعمل التفريغ على المعالج.")
    elif hw.get("cuda") and not hw.get("cublas"):
        why.append(
            "لديك بطاقة رسوميات NVIDIA، لكن مكتبة cuBLAS 12 من حزمة CUDA غير مثبّتة، فيعمل التفريغ على المعالج. "
            "ثبّت CUDA Toolkit 12 من موقع NVIDIA ثم أعد تشغيل ترجمان ليستعمل البطاقة."
        )
    if ram >= 12 and threads >= 16:
        why.append(f"معالجك فيه {threads} مسارًا وذاكرتك {ram:g} غيغابايت: يشغّل large-v3-turbo، أدقّ ما يناسب المعالج للعربية، بسرعة مقبولة.")
        return {"model": "large-v3-turbo", "device": "cpu", "short": "large-v3-turbo", "why": why}
    if ram >= 6 and threads >= 4:
        short = "large-v3" if ram >= 12 else "large-v3-turbo" if ram >= 8 else "small"
        slow = seconds_per_minute(short, hw, "cpu")
        why.append(
            f"معالجك فيه {threads} مسارات وذاكرتك {ram:g} غيغابايت: نموذج small يكتب العربية صحيحة "
            f"في قرابة {seconds_per_minute('small', hw, 'cpu')} ثانية لكل دقيقة صوت."
        )
        if short != "small":
            why.append(
                f"وفي الوضع التلقائي تُفرَّغ التسجيلات القصيرة (حتى دقيقتين، مثل الرسائل الصوتية) بنموذج {short} الأدق، "
                "وهو الأفضل في اللهجات والأسماء والكلمات الإنجليزية، مع أنه أبطأ "
                f"(قرابة {round(slow / 60, 1):g} دقيقة لكل دقيقة صوت)؛ والأطول بنموذج small حتى لا يطول الانتظار."
            )
        return {"model": "small", "device": "cpu", "short": short, "why": why}
    why.append(f"ذاكرة الجهاز {ram:g} غيغابايت ومعالجه {threads} مسارات: النماذج الأكبر من base قد تُبطئ الجهاز كثيرًا.")
    return {"model": "base", "device": "cpu", "short": "small" if ram >= 4 else "base", "why": why}


def model_warning(model: str, device: str, hw: dict[str, Any]) -> str:
    """Why a choice may be a bad idea on this computer ("" when it is fine)."""
    info = MODELS[model]
    ram = float(hw.get("ramGb") or 0)
    if device == "cpu" and ram and info["ram"] > ram * 0.6:
        return f"يحتاج قرابة {info['ram']:g} غيغابايت من الذاكرة، وهذا كثير على جهاز ذاكرته {ram:g} غيغابايت."
    spm = seconds_per_minute(model, hw, device)
    if spm >= 90:
        return f"بطيء على هذا الجهاز: قرابة {round(spm / 60, 1):g} دقيقة لكل دقيقة من الصوت."
    return ""


class AsrSettings:
    def __init__(self, file: Path, env_model: str = ""):
        self.file = file
        self.env_model = env_model if env_model in MODELS else ""
        self.values: dict[str, Any] = dict(DEFAULTS)

    def load(self) -> "AsrSettings":
        j = read_json(self.file, {}) or {}
        self.values = dict(DEFAULTS)
        self._apply(j)
        return self

    def save(self) -> None:
        write_json(self.file, self.values, indent=1)

    def _apply(self, j: dict[str, Any]) -> None:
        v = self.values
        if j.get("model") in (*MODELS, "auto"):
            v["model"] = j["model"]
        if j.get("device") in ("auto", "cpu", "cuda"):
            v["device"] = j["device"]
        lang = str(j.get("language") or "").lower()
        if lang == "auto" or _known_language(lang):
            v["language"] = lang
        if j.get("style") in STYLES:
            v["style"] = j["style"]
        if j.get("quality") in ("accurate", "fast"):
            v["quality"] = j["quality"]
        for k in ("enhance", "vad", "aiFix"):
            if k in j:
                v[k] = bool(j[k])
        if "terms" in j:
            v["terms"] = clean_terms(j.get("terms"))
        elif j.get("vocab"):  # the first version kept one text field: each line becomes a row
            v["terms"] = clean_terms([{"from": "", "to": w} for w in split_words(str(j["vocab"]))])

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        self._apply(changes or {})
        self.save()
        return dict(self.values)

    def effective(self, hw: dict[str, Any] | None = None, duration: float | None = None) -> dict[str, Any]:
        """What a transcription will actually use, after "auto" and what the computer can do. With the
        length of the recording, "auto" gives a short one the more accurate model."""
        hw = hw or hardware()
        rec = recommend(hw, arabic=self.values["language"] == "ar")
        v = self.values
        if v["model"] != "auto":
            model = v["model"]
        elif self.env_model:
            model = self.env_model
        elif duration and duration <= SHORT_SECONDS:
            model = rec.get("short") or rec["model"]
        else:
            model = rec["model"]
        if v["device"] == "cuda":
            device = "cuda" if gpu_usable(hw, allow_old=True) else "cpu"
        elif v["device"] == "cpu":
            device = "cpu"
        else:
            device = "cuda" if gpu_usable(hw) else "cpu"
        return {
            "model": model,
            "device": device,
            # On a card, CTranslate2 picks what it supports (older cards have no float16).
            "compute": "auto" if device == "cuda" else "int8",
            "threads": cpu_threads(hw),
            "beam": 5 if v["quality"] == "accurate" else 1,
            "language": None if v["language"] == "auto" else v["language"],
            "prompt": PROMPTS.get(v["style"], ""),
            "enhance": bool(v["enhance"]),
            "vad": bool(v["vad"]),
            "hotwords": hint_words(v["terms"]),
            "terms": [t for t in v["terms"] if t["from"]],
            "secondsPerMinute": seconds_per_minute(model, hw, device),
        }

    def public(self, duration: float | None = None) -> dict[str, Any]:
        hw = hardware()
        eff = self.effective(hw, duration)
        return {
            "settings": dict(self.values),
            "hardware": hw,
            "recommended": recommend(hw, arabic=self.values["language"] == "ar"),
            "effective": eff,
            "models": [
                {
                    "id": k, **m,
                    "secondsPerMinute": seconds_per_minute(k, hw, eff["device"]),
                    "warning": model_warning(k, eff["device"], hw),
                    "downloaded": model_downloaded(k),
                    "arabicOnly": bool(m.get("arabicOnly")),
                    "diskMb": round(model_disk_bytes(k) / 1_000_000),
                }
                for k, m in MODELS.items()
            ],
            "styles": list(STYLES),
            "languages": list(LANGS),
        }


def split_words(text: str) -> list[str]:
    import re

    return [w.strip() for w in re.split(r"[\n,،;؛]+", text or "") if w.strip()]


def clean_terms(rows: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        frm = " ".join(str(r.get("from") or "").split())[:TERM_LEN]
        to = " ".join(str(r.get("to") or "").split())[:TERM_LEN]
        if to and (frm, to) not in seen:
            seen.add((frm, to))
            out.append({"from": frm, "to": to})
    return out[:TERMS_MAX]


def hint_words(terms: list[dict[str, str]]) -> str:
    """How the words should be written, as Whisper's hint: "Excel، Zoom، كريم"."""
    seen: list[str] = []
    for t in terms:
        if t["to"] not in seen:
            seen.append(t["to"])
    return "، ".join(seen[:60])


def apply_terms(text: str, terms: list[dict[str, str]]) -> str:
    """Replaces what Whisper wrote ("from") with how the user writes it ("to"), whole words only, also
    after the Arabic article and the joined prepositions: "السارم" -> "ال CRM" when "سارم" -> "CRM"."""
    import re

    for t in sorted(terms, key=lambda x: -len(x["from"])):
        frm = t.get("from") or ""
        if not frm:
            continue
        pattern = r"(?<![\w])((?:[وفبلك]?ال|[وفبلك])?)" + re.escape(frm) + r"(?![\w])"
        text = re.sub(pattern, lambda m: (m.group(1) + " " if m.group(1) and _latin(t["to"]) else m.group(1)) + t["to"], text)
    return text


def _latin(s: str) -> bool:
    return bool(s) and s[0].isascii()


def _known_language(code: str) -> bool:
    try:
        from faster_whisper.tokenizer import _LANGUAGE_CODES  # type: ignore

        return code in _LANGUAGE_CODES
    except Exception:  # noqa: BLE001
        return code in LANGS


def model_repo(name: str) -> str:
    if name in REPOS:
        return REPOS[name][0]
    try:
        from faster_whisper.utils import _MODELS  # type: ignore

        return _MODELS.get(name, f"Systran/faster-whisper-{name}")
    except Exception:  # noqa: BLE001
        return f"Systran/faster-whisper-{name}"


def model_downloaded(name: str) -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache  # type: ignore

        rev = REPOS[name][1] if name in REPOS else None
        hit = try_to_load_from_cache(model_repo(name), "model.bin", revision=rev)
        return isinstance(hit, str) and os.path.exists(hit)
    except Exception:  # noqa: BLE001
        return False


def _hub() -> Path:
    return Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"


def _repo_dir(name: str) -> Path:
    return _hub() / ("models--" + model_repo(name).replace("/", "--"))


def _repo_files(name: str) -> list[Path]:
    """The real files of a downloaded model (links are followed to what they point at)."""
    root, hub = _repo_dir(name), _hub().resolve()
    out: list[Path] = []
    if not root.exists():
        return out
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            p = Path(dirpath) / f
            try:
                real = p.resolve()
            except OSError:
                continue
            if real.is_file() and hub in real.parents and real not in out:
                out.append(real)
    return out


def model_disk_bytes(name: str) -> int:
    total = 0
    for p in _repo_files(name):
        try:
            total += p.stat().st_size
        except OSError:
            pass
    return total


def delete_model(name: str) -> int:
    """Removes a downloaded model from the disk; returns the bytes freed."""
    if name not in MODELS:
        return 0
    freed = 0
    for p in _repo_files(name):
        try:
            size = p.stat().st_size
            p.unlink()
            freed += size
        except OSError:
            pass
    shutil.rmtree(_repo_dir(name), ignore_errors=True)
    return freed


def hub_bytes() -> int:
    """Bytes in the model download folder; growing while a model downloads (shown as progress)."""
    root = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"
    total = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total
