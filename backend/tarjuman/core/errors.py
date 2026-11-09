from __future__ import annotations


class AppError(Exception):
    """An error with a stable machine code (see docs/specs.md §4) and a human message."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class Cancelled(AppError):
    def __init__(self) -> None:
        super().__init__("CANCELLED", "اتلغت")


def error_code(e: BaseException) -> str:
    return getattr(e, "code", None) or "ERROR"
