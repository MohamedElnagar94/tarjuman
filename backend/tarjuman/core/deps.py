"""Optional Python packages: is one installed? (Checked without importing it, which can be slow.)"""

from __future__ import annotations

from importlib.util import find_spec


def has(module: str) -> bool:
    try:
        return find_spec(module) is not None
    except (ImportError, ValueError):
        return False
