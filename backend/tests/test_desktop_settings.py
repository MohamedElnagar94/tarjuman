"""The desktop app's lifecycle settings and its sign-in entry (with a fake registry)."""

import os

import pytest

from tarjuman import desktop_settings as ds
from tarjuman.desktop_settings import DesktopSettings, after_window_closed


class FakeReg:
    """Just enough of winreg for the Run key."""

    HKEY_CURRENT_USER = "HKCU"
    KEY_SET_VALUE = KEY_READ = 0
    REG_SZ = 1

    def __init__(self):
        self.values: dict[str, str] = {}

    def OpenKey(self, root, path, reserved, access):
        assert root == "HKCU" and path == ds.RUN_KEY
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def SetValueEx(self, key, name, reserved, kind, value):
        self.values[name] = value

    def DeleteValue(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        del self.values[name]

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(name)
        return self.values[name], self.REG_SZ


def test_settings_start_off_and_are_kept(tmp_path):
    s = DesktopSettings(tmp_path / "desktop.json").load()
    assert s.values == {"minimizeToTray": False, "closeToTray": False, "startWithWindows": False, "keepEngine": False}
    s.update({"closeToTray": True, "keepEngine": 1, "unknown": True})
    again = DesktopSettings(tmp_path / "desktop.json").load()
    assert again["closeToTray"] is True and again["keepEngine"] is True and "unknown" not in again.values


def test_start_with_windows_writes_and_removes_the_sign_in_entry(tmp_path, monkeypatch):
    reg = FakeReg()
    monkeypatch.setattr(ds, "_winreg", lambda: reg)
    monkeypatch.setattr(ds, "supported", lambda: True)
    s = DesktopSettings(tmp_path / "desktop.json").load()
    s.update({"startWithWindows": True})
    cmd = reg.values["Tarjuman"]
    assert "'--background'" in cmd and "tarjuman.__main__" in cmd
    if os.name == "nt":
        assert "pythonw" in cmd.lower(), "no console window at sign-in"
    assert s.public()["startWithWindows"] is True
    s.update({"startWithWindows": False})
    assert reg.values == {} and s.public()["startWithWindows"] is False
    s.update({"startWithWindows": False})  # turning it off twice is fine


def test_startup_command_uses_pythonw_and_names_the_backend(tmp_path):
    cmd = ds.startup_command(python=str(tmp_path / "python.exe"), backend=tmp_path / "backend")
    assert cmd.startswith(f'"{tmp_path / "pythonw.exe"}" -c "')
    assert f"r'{tmp_path / 'backend'}'" in cmd


@pytest.mark.parametrize(
    "settings, jobs, expected",
    [
        ({}, 0, "quit"),
        ({}, 2, "ask-quit"),
        ({"closeToTray": True}, 0, "tray-stop"),
        ({"closeToTray": True}, 1, "ask-stop"),
        ({"keepEngine": True}, 0, "tray"),
        ({"keepEngine": True, "closeToTray": True}, 3, "tray"),
        ({"minimizeToTray": True}, 0, "quit"),  # minimizing is a separate choice
        ({"startWithWindows": True}, 0, "quit"),  # so is starting with Windows
    ],
)
def test_what_closing_the_window_does(settings, jobs, expected):
    assert after_window_closed(settings, jobs) == expected
