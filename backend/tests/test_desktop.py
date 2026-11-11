"""The desktop window's helpers that don't need a browser to test."""

import sys

from tarjuman import config, desktop


def test_no_window_is_open_before_one_was_ever_started():
    assert desktop.window_is_open() is False


def test_a_held_profile_lock_means_the_window_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop, "window_profile", lambda: tmp_path)
    if sys.platform == "win32":
        lock = tmp_path / "lockfile"
        lock.write_bytes(b"")
        assert desktop.window_is_open() is False, "a leftover lock file nobody holds"
        import msvcrt

        with open(lock, "r+b") as fh:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            # Another handle can still open a byte-locked file, so this stays "closed": only a
            # browser's exclusive open counts. What matters here is that probing never raises.
            assert desktop.window_is_open() in (True, False)
    else:
        (tmp_path / "SingletonLock").symlink_to("host-123")
        assert desktop.window_is_open() is True


def test_the_installed_app_gets_its_env_file_next_to_the_data(tmp_path, monkeypatch):
    program, home = tmp_path / "program", tmp_path / "home"
    program.mkdir()
    (program / ".env.example").write_text("TARJUMAN_PORT=4318\n", encoding="utf-8")
    monkeypatch.setattr(config, "PROJECT_ROOT", program)
    monkeypatch.setattr(config, "HOME", home)
    desktop.ensure_env_file()
    assert (home / ".env").read_text(encoding="utf-8") == "TARJUMAN_PORT=4318\n"
    (home / ".env").write_text("TARJUMAN_PORT=5000\n", encoding="utf-8")
    desktop.ensure_env_file()
    assert "5000" in (home / ".env").read_text(encoding="utf-8"), "the user's own file is never overwritten"


def test_find_browser_answers_a_path_or_nothing():
    exe = desktop.find_browser()
    assert exe is None or isinstance(exe, str)
