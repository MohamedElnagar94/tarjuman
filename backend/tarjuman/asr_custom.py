"""A speech-to-text model the user picks: any Whisper model in faster-whisper's format (CTranslate2),
named by its Hugging Face repository ("owner/name") or by a folder on this computer.

Before anything is downloaded the model is looked at: its format, that it is Whisper, its size and
licence. A model in another format is refused with the reason, instead of failing after gigabytes.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .core.errors import AppError

HF_ID = re.compile(r"^[A-Za-z0-9][\w.-]{0,95}/[A-Za-z0-9][\w.-]{0,95}$")
HF_API = "https://huggingface.co/api/models/"
HF_FILE = "https://huggingface.co/{id}/resolve/{rev}/config.json"
# Keys every Whisper model converted for CTranslate2 has in its config.json.
WHISPER_KEYS = ("alignment_heads", "lang_ids", "suppress_ids", "suppress_ids_begin")
TRANSFORMERS_FILES = ("model.safetensors", "pytorch_model.bin", "model.safetensors.index.json")


def _is_whisper_config(cfg: dict[str, Any]) -> bool:
    return any(k in cfg for k in WHISPER_KEYS)


def name_of(source: str) -> str:
    return source.rstrip("/\\").split("/")[-1].split("\\")[-1]


async def inspect(source: str) -> dict[str, Any]:
    """{id, kind: "hf"|"dir", name, revision, sizeMb, license}. Raises AppError with the reason."""
    source = (source or "").strip().strip('"')
    if source.startswith("https://huggingface.co/"):
        source = "/".join(source.split("huggingface.co/", 1)[1].split("/")[:2])
    if not source:
        raise AppError("CUSTOM_EMPTY", "اكتب اسم النموذج على Hugging Face أو مسار مجلده على جهازك.")
    if os.path.isabs(source) or source.startswith((".", "~")) or "\\" in source:
        return _inspect_dir(Path(os.path.expanduser(source)))
    if not HF_ID.match(source):
        raise AppError("CUSTOM_BAD", "الاسم يجب أن يكون بالشكل owner/name، مثل SohailElsek/whisper-large-v3-arabic-dialectal-v2-ct2")
    return await _inspect_hf(source)


def _inspect_dir(folder: Path) -> dict[str, Any]:
    if not folder.is_dir():
        raise AppError("CUSTOM_NOT_FOUND", f"لا يوجد مجلد بهذا المسار: {folder}")
    names = {p.name for p in folder.iterdir() if p.is_file()}
    if "model.bin" not in names:
        if names & set(TRANSFORMERS_FILES):
            raise AppError("CUSTOM_FORMAT", "هذا النموذج بصيغة Transformers، وترجمان يحتاج صيغة CTranslate2 (faster-whisper). حوّله أولًا بأداة ct2-transformers-converter.")
        raise AppError("CUSTOM_FORMAT", "المجلد لا يحتوي model.bin، فليس نموذجًا بصيغة faster-whisper.")
    try:
        cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    if not _is_whisper_config(cfg):
        raise AppError("CUSTOM_NOT_WHISPER", "هذا النموذج ليس Whisper، وترجمان لا يشغّل إلا نماذج Whisper.")
    size = sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
    return {"id": str(folder.resolve()), "kind": "dir", "name": folder.name, "revision": "", "sizeMb": round(size / 1e6), "license": ""}


async def _config(repo: str, rev: str) -> dict[str, Any]:
    from .core import http

    try:
        cfg = (await http.client().get(HF_FILE.format(id=repo, rev=rev or "main"), timeout=20.0, follow_redirects=True)).json()
    except Exception:  # noqa: BLE001
        return {}
    return cfg if isinstance(cfg, dict) else {}


async def _inspect_hf(repo: str) -> dict[str, Any]:
    from .core import http

    try:
        r = await http.client().get(HF_API + repo, params={"blobs": "true"}, timeout=20.0)
    except Exception as e:  # noqa: BLE001
        raise AppError("CUSTOM_NETWORK", "تعذّر الوصول إلى Hugging Face. تأكد من الاتصال بالإنترنت.") from e
    if r.status_code in (401, 404):
        # Hugging Face answers the same for a name that doesn't exist and for a private model.
        raise AppError("CUSTOM_NOT_FOUND", "لا يوجد نموذج عام بهذا الاسم على Hugging Face. تأكد من كتابة الاسم كما في صفحته.")
    if r.status_code == 403:
        raise AppError("CUSTOM_PRIVATE", "هذا النموذج يحتاج موافقة على شروطه في صفحته، فلا يمكن تنزيله.")
    if r.status_code >= 400:
        raise AppError("CUSTOM_NETWORK", f"ردّ Hugging Face بخطأ ({r.status_code}).")
    j = r.json()
    if j.get("gated") or j.get("private"):
        raise AppError("CUSTOM_PRIVATE", "هذا النموذج خاص أو يحتاج موافقة على شروطه، فلا يمكن تنزيله.")
    files = {s.get("rfilename"): s.get("size") or 0 for s in j.get("siblings") or []}
    rev = str(j.get("sha") or "")
    cfg = await _config(repo, rev) if "config.json" in files else {}
    if "model.bin" not in files:
        if cfg.get("model_type") and cfg.get("model_type") != "whisper":
            raise AppError("CUSTOM_NOT_WHISPER", "هذا النموذج ليس Whisper، وترجمان لا يشغّل إلا نماذج Whisper.")
        if set(files) & set(TRANSFORMERS_FILES):
            raise AppError(
                "CUSTOM_FORMAT",
                "هذا النموذج بصيغة Transformers، وترجمان يحتاج صيغة CTranslate2 (faster-whisper). "
                "ابحث عن نسخة منه تنتهي بـ ct2 أو عليها علامة faster-whisper.",
            )
        raise AppError("CUSTOM_FORMAT", "لا يحتوي هذا النموذج ملف model.bin، فليس بصيغة faster-whisper.")
    if not _is_whisper_config(cfg):
        raise AppError("CUSTOM_NOT_WHISPER", "هذا النموذج ليس Whisper، وترجمان لا يشغّل إلا نماذج Whisper.")
    card = j.get("cardData") or {}
    lic = card.get("license") or ""
    return {
        "id": repo,
        "kind": "hf",
        "name": name_of(repo),
        "revision": rev,
        "sizeMb": round(sum(files.values()) / 1e6),
        "license": lic if isinstance(lic, str) else ", ".join(map(str, lic)),
    }
