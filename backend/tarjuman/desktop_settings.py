"""The desktop app's lifecycle settings (Windows): what minimizing and closing the window do, starting
with Windows, and whether the engine keeps running after the window is closed.

They are four separate choices. Closing the window keeps Tarjuman in the notification area when
either "close to tray" or "keep the engine running" is on: the second needs the icon too, so the user
can always quit. Only "keep the engine running" decides whether the local server stays up for the
browser extension and running jobs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .core.store import read_json, write_json

DEFAULTS: dict[str, bool] = {
    "minimizeToTray": False,
    "closeToTray": False,
    "startWithWindows": False,
    "keepEngine": False,
    # Updates (Settings -> Updates): look for a new version every few hours, and install it without asking.
    "checkUpdates": True,
    "autoUpdate": False,
}
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Tarjuman"


class DesktopSettings:
    def __init__(self, file: Path):
        self.file = file
        self.values: dict[str, bool] = dict(DEFAULTS)

    def load(self) -> "DesktopSettings":
        j = read_json(self.file, {})
        self.values = {k: bool(j.get(k, v)) for k, v in DEFAULTS.items()}
        return self

    def save(self) -> None:
        write_json(self.file, self.values, indent=1)

    def __getitem__(self, key: str) -> bool:
        return self.values[key]

    def update(self, changes: dict[str, Any]) -> dict[str, bool]:
        """Applies the known keys; "startWithWindows" is also written to Windows at once."""
        for k in DEFAULTS:
            if k in changes:
                self.values[k] = bool(changes[k])
        if "startWithWindows" in changes and supported():
            set_start_with_windows(self.values["startWithWindows"])
        self.save()
        return dict(self.values)

    def public(self) -> dict[str, Any]:
        out: dict[str, Any] = dict(self.values)
        if supported():
            out["startWithWindows"] = start_with_windows_enabled()  # what Windows has, not only what was saved
        return out


def supported() -> bool:
    return sys.platform == "win32"


def startup_command(python: str | None = None, backend: Path | None = None) -> str:
    """The command Windows runs at sign-in: the app in the notification area, without a window and
    without a console. It names the backend folder itself, so it works from source and installed."""
    from . import config

    exe = Path(python or sys.executable)
    pythonw = exe.with_name("pythonw.exe") if exe.name.lower() == "python.exe" else exe
    folder = backend or config.PROJECT_ROOT / "backend"
    code = (
        f"import sys; sys.path.insert(0, r'{folder}'); "
        "from tarjuman.__main__ import main; main(['app', '--background'])"
    )
    return f'"{pythonw}" -c "{code}"'


def _winreg():
    import winreg

    return winreg


def set_start_with_windows(on: bool, reg=None) -> None:
    """Adds or removes Tarjuman in the current user's sign-in programs (Task Manager → Startup shows it)."""
    reg = reg or _winreg()
    with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY, 0, reg.KEY_SET_VALUE) as key:
        if on:
            reg.SetValueEx(key, RUN_VALUE, 0, reg.REG_SZ, startup_command())
        else:
            try:
                reg.DeleteValue(key, RUN_VALUE)
            except FileNotFoundError:
                pass


def start_with_windows_enabled(reg=None) -> bool:
    reg = reg or _winreg()
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_KEY, 0, reg.KEY_READ) as key:
            reg.QueryValueEx(key, RUN_VALUE)
            return True
    except OSError:
        return False


def after_window_closed(values: dict[str, bool], jobs: int) -> str:
    """What to do when the app window has been closed:
    "tray"        stay in the notification area, engine running
    "tray-stop"   stay in the notification area, stop the engine
    "ask-stop"    jobs are running and the engine would stop: ask first
    "quit"        quit
    "ask-quit"    jobs are running and Tarjuman would quit: ask first
    """
    if values.get("keepEngine"):
        return "tray"
    if values.get("closeToTray"):
        return "ask-stop" if jobs else "tray-stop"
    return "ask-quit" if jobs else "quit"
