"""The Windows desktop app with its notification-area (system tray) icon.

This process owns the local server ("the engine") and the app window, and keeps the icon. What
minimizing and closing the window do is set by the four desktop settings (``desktop_settings``):

- minimize to tray: a minimized window is hidden; the icon brings it back.
- close to tray: closing the window keeps Tarjuman in the notification area.
- keep the engine running: the server stays up after the window is closed, for the browser extension
  and for running jobs. Without it, the engine stops with the window and the icon restarts it.
- start with Windows: handled by ``desktop_settings`` (a sign-in entry that starts this in the tray).

The window is Edge or Chrome in app mode (``desktop.open_window``): it can't be told what its own
buttons do, so this process watches it, hides it when it is minimized, and reacts when it closes.
Nothing here polls the network; the watch is a local check twice a second.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
import os
import threading
import time
import webbrowser

from . import config, desktop
from .core.deps import has
from .desktop_settings import DesktopSettings, after_window_closed
from .updates import Updater

log = logging.getLogger("tarjuman.tray")

SW_HIDE, SW_SHOW, SW_RESTORE = 0, 5, 9
WM_CLOSE = 0x0010
GW_OWNER = 4
MB_YESNO, MB_ICONQUESTION, MB_SETFOREGROUND, MB_TOPMOST = 0x4, 0x20, 0x10000, 0x40000
IDYES = 6

TEXT = {
    "en": {
        "open": "Open Tarjuman",
        "engineOn": "Engine running",
        "engineJobs": "Engine running, jobs in progress: {n}",
        "engineOff": "Engine stopped",
        "extOk": "Browser extension: approved",
        "extNone": "Browser extension: not set up",
        "logs": "Open the data folder",
        "quit": "Quit Tarjuman",
        "tipIdle": "Tarjuman: ready",
        "tipBusy": "Tarjuman: jobs in progress: {n}",
        "tipOff": "Tarjuman: engine stopped",
        "askQuit": "Tarjuman is still working (jobs in progress: {n}).\n\n"
        "Yes: keep it running in the notification area.\nNo: stop the jobs and quit.",
        "askStop": "Tarjuman is still working (jobs in progress: {n}).\n\n"
        "Yes: keep the engine running until you quit.\nNo: stop the jobs and the engine now.",
        "askTrayQuit": "Tarjuman is still working (jobs in progress: {n}).\n\nStop the jobs and quit?",
    },
    "ar": {
        "open": "افتح ترجمان",
        "engineOn": "المحرك يعمل",
        "engineJobs": "المحرك يعمل، والمهام الجارية: {n}",
        "engineOff": "المحرك متوقف",
        "extOk": "إضافة المتصفح: موافَق عليها",
        "extNone": "إضافة المتصفح: غير مثبّتة",
        "logs": "افتح مجلد البيانات",
        "quit": "أغلق ترجمان",
        "tipIdle": "ترجمان: جاهز",
        "tipBusy": "ترجمان: المهام الجارية: {n}",
        "tipOff": "ترجمان: المحرك متوقف",
        "askQuit": "ما زال ترجمان يعمل (المهام الجارية: {n}).\n\n"
        "نعم: أبقِه يعمل في منطقة الإعلامات.\nلا: أوقف المهام وأغلق ترجمان.",
        "askStop": "ما زال ترجمان يعمل (المهام الجارية: {n}).\n\n"
        "نعم: أبقِ المحرك يعمل حتى تغلق ترجمان.\nلا: أوقف المهام والمحرك الآن.",
        "askTrayQuit": "ما زال ترجمان يعمل (المهام الجارية: {n}).\n\nهل توقف المهام وتغلق ترجمان؟",
    },
}


def available() -> bool:
    """The tray needs Windows and the pystray and Pillow packages (installed with the app)."""
    return os.name == "nt" and all(has(m) for m in ("pystray", "PIL", "psutil"))


def _user32():
    u = ctypes.windll.user32
    u.IsWindow.argtypes = u.IsWindowVisible.argtypes = u.IsIconic.argtypes = [wt.HWND]
    u.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
    u.SetForegroundWindow.argtypes = [wt.HWND]
    u.GetWindowTextLengthW.argtypes = [wt.HWND]
    u.GetWindow.argtypes = [wt.HWND, wt.UINT]
    u.GetWindow.restype = wt.HWND
    u.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    u.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    u.MessageBoxW.argtypes = [wt.HWND, wt.LPCWSTR, wt.LPCWSTR, wt.UINT]
    return u


def _arabic_windows() -> bool:
    try:
        return (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x01  # LANG_ARABIC
    except Exception:  # noqa: BLE001
        return False


class DesktopApp:
    def __init__(self, host: str, port: int, free_port, settings: DesktopSettings):
        self.host, self.base_port, self.free_port = host, port, free_port
        self.settings = settings
        self.user32 = _user32()
        self.lang = "ar" if _arabic_windows() else "en"
        self.lock = threading.Lock()
        self.server = None
        self.thread: threading.Thread | None = None
        self.app = None
        self.url = ""
        self.hwnd = 0
        self.ext_allowed = False
        self.quitting = False
        self.icon = None
        self.updater = Updater()

    def t(self, key: str, **kw) -> str:
        return TEXT[self.lang][key].format(**kw)

    # ---------------- engine ----------------

    @property
    def engine_running(self) -> bool:
        s = self.server
        return s is not None and not s.should_exit

    def start_engine(self) -> None:
        import uvicorn

        from .api.app import create_app

        with self.lock:
            if self.engine_running:
                return
            port = self.free_port(self.host, self.base_port)
            self.app = create_app(port=port, desktop=self)
            self.server = uvicorn.Server(
                uvicorn.Config(self.app, host=self.host, port=port, log_level="warning", log_config=None)
            )
            self.thread = threading.Thread(target=self.server.run, name="server", daemon=True)
            self.thread.start()
            for _ in range(400):
                if self.server.started:
                    break
                time.sleep(0.05)
            self.url = f"http://127.0.0.1:{port}"
        log.info("engine started at %s", self.url)
        desktop.ensure_voice_in_background()

    def stop_engine(self) -> None:
        """Stops the server; its shutdown cancels running jobs and saves the caches."""
        with self.lock:
            server, thread = self.server, self.thread
            self.server = None
        if server is not None:
            self.ext_allowed = self._extension_allowed()
            server.should_exit = True
            if thread is not None:
                thread.join(15)
            log.info("engine stopped")

    def jobs(self) -> int:
        try:
            return self.app.state.services.jobs.running_count() if self.engine_running else 0
        except Exception:  # noqa: BLE001
            return 0

    def _extension_allowed(self) -> bool:
        try:
            return bool(self.app.state.extensions.allowed) if self.app is not None else self.ext_allowed
        except Exception:  # noqa: BLE001
            return self.ext_allowed

    # ---------------- window ----------------

    def _our_pids(self) -> set[int]:
        """The browser processes that use the app window's own profile (not the user's own browser)."""
        import psutil

        profile = str(desktop.window_profile()).lower()
        pids: set[int] = set()
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                if (p.info["name"] or "").lower() in ("msedge.exe", "chrome.exe") and profile in " ".join(
                    p.info["cmdline"] or []
                ).lower():
                    pids.add(p.pid)
            except (psutil.Error, TypeError):
                continue
        return pids

    def find_window(self) -> int:
        u = self.user32
        if self.hwnd and u.IsWindow(self.hwnd):
            return self.hwnd
        pids = self._our_pids()
        found: list[int] = []

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def each(h, _):
            pid = wt.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if pid.value in pids and u.IsWindowVisible(h) and u.GetWindowTextLengthW(h) > 0 and not u.GetWindow(h, GW_OWNER):
                found.append(h)
            return True

        u.EnumWindows(each, 0)
        self.hwnd = found[0] if found else 0
        return self.hwnd

    def show_window(self) -> None:
        """Brings the window back from the tray, or opens a new one (starting the engine if needed)."""
        if not self.engine_running:
            self.start_engine()
        if desktop.window_is_open():
            h = self.find_window()
            if h:
                self.user32.ShowWindow(h, SW_RESTORE)
                self.user32.ShowWindow(h, SW_SHOW)
                self.user32.SetForegroundWindow(h)
                return
        self.hwnd = 0
        if desktop.open_window(self.url) is None:
            webbrowser.open(self.url)

    def close_window(self) -> None:
        if desktop.window_is_open():
            h = self.find_window()
            if h:
                self.user32.PostMessageW(h, WM_CLOSE, 0, 0)

    # ---------------- decisions ----------------

    def ask(self, text: str) -> bool:
        flags = MB_YESNO | MB_ICONQUESTION | MB_SETFOREGROUND | MB_TOPMOST
        return self.user32.MessageBoxW(None, text, "Tarjuman", flags) == IDYES

    def on_window_closed(self) -> None:
        n = self.jobs()
        what = after_window_closed(self.settings.values, n)
        if what == "ask-quit":
            what = "tray" if self.ask(self.t("askQuit", n=n)) else "quit"
        elif what == "ask-stop":
            what = "tray" if self.ask(self.t("askStop", n=n)) else "tray-stop"
        log.info("window closed: %s", what)
        if what == "quit":
            self.quit(confirm=False)
        elif what == "tray-stop":
            self.stop_engine()

    def quit(self, confirm: bool = True) -> None:
        n = self.jobs()
        if confirm and n and not self.ask(self.t("askTrayQuit", n=n)):
            return
        self.quitting = True
        self.close_window()
        self.stop_engine()
        if self.icon is not None:
            self.icon.stop()

    # ---------------- updates ----------------

    def auto_update(self) -> None:
        """Looks for a new version a little after start and then every few hours. With "install updates
        automatically" on, installs it once no job is running (Windows asks for permission first)."""
        time.sleep(30)
        while not self.quitting:
            try:
                if self.settings["checkUpdates"]:
                    self.updater.check()
                    st = self.updater.state()
                    if st["available"] and self.settings["autoUpdate"] and st["canInstall"] and self.jobs() == 0:
                        log.info("installing update %s by itself", st["latest"])
                        self.updater.start_install(on_ready=lambda: self.quit(confirm=False))
            except Exception:  # noqa: BLE001
                log.exception("update check failed")
            for _ in range(600):  # ten minutes, then look again (check() itself waits hours between asks)
                if self.quitting:
                    return
                time.sleep(1)

    # ---------------- icon ----------------

    def status_text(self) -> str:
        if not self.engine_running:
            return self.t("engineOff")
        n = self.jobs()
        return self.t("engineJobs", n=n) if n else self.t("engineOn")

    def tooltip(self) -> str:
        if not self.engine_running:
            return self.t("tipOff")
        n = self.jobs()
        return self.t("tipBusy", n=n) if n else self.t("tipIdle")

    def watch(self) -> None:
        """Hides a minimized window when asked to, and notices when the window closes."""
        was_open = False
        title = ""
        while not self.quitting:
            if desktop.window_is_open():
                was_open = True
                if self.settings["minimizeToTray"]:
                    h = self.find_window()
                    if h and self.user32.IsIconic(h) and self.user32.IsWindowVisible(h):
                        self.user32.ShowWindow(h, SW_HIDE)
            elif was_open:
                was_open = False
                self.hwnd = 0
                self.on_window_closed()
            tip = self.tooltip()
            if tip != title and self.icon is not None:
                self.icon.title = title = tip
            time.sleep(0.5)

    def run(self, background: bool = False) -> None:
        import pystray
        from PIL import Image

        def later(fn):
            # Menu actions run off the icon's thread, so a slow start never freezes the menu.
            return lambda icon, item: threading.Thread(target=fn, daemon=True).start()

        menu = pystray.Menu(
            pystray.MenuItem(lambda item: self.t("open"), later(self.show_window), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: self.status_text(), None, enabled=False),
            pystray.MenuItem(
                lambda item: self.t("extOk") if self._extension_allowed() else self.t("extNone"), None, enabled=False
            ),
            pystray.MenuItem(lambda item: self.t("logs"), later(lambda: os.startfile(config.DATA))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: self.t("quit"), later(self.quit)),
        )
        image = Image.open(config.PROJECT_ROOT / "assets" / "brand" / "icon-64.png")
        self.icon = pystray.Icon("tarjuman", image, "Tarjuman", menu)

        def setup(icon) -> None:
            icon.visible = True
            try:
                self.start_engine()
                if not background:
                    self.show_window()
                threading.Thread(target=self.auto_update, name="updates", daemon=True).start()
                self.watch()
            except Exception:  # noqa: BLE001
                log.exception("desktop app failed")
                self.quit(confirm=False)

        self.icon.run(setup=setup)
        self.stop_engine()
