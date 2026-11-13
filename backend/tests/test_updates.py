"""Updates from GitHub releases: which ones are newer, and installing only a verified download."""

import hashlib
import time

from tarjuman import updates
from tarjuman.updates import Updater, newer_releases, parse_version


def release(tag, body="", exe=True, sha=True, draft=False, pre=False, appimage=False):
    v = tag.lstrip("v")
    name = f"Tarjuman-{v}-x86_64.AppImage" if appimage else f"Tarjuman-Setup-{v}.exe"
    assets = []
    if exe:
        assets.append({"name": name, "browser_download_url": f"https://x/{name}", "size": 10})
    if sha:
        assets.append({"name": name + ".sha256", "browser_download_url": f"https://x/{name}.sha256"})
    return {"tag_name": tag, "body": body, "assets": assets, "draft": draft, "prerelease": pre,
            "published_at": "2026-11-13T00:00:00Z", "html_url": f"https://github.com/x/releases/{tag}"}


def test_versions_compare_as_numbers():
    assert parse_version("v3.10.0") > parse_version("3.9.9")
    assert parse_version("nightly") is None


def test_only_newer_published_releases_newest_first():
    got = newer_releases(
        [release("v3.0.0"), release("v3.2.0", "two"), release("v3.1.0", "one"), release("v3.3.0", draft=True),
         release("v3.4.0-beta"), release("v3.5.0", pre=True)],
        "3.0.0",
    )
    assert [r["version"] for r in got] == ["3.2.0", "3.1.0"], "drafts, pre-releases and odd tags are skipped"
    assert got[0]["notes"] == "two" and got[0]["installer"]["name"] == "Tarjuman-Setup-3.2.0.exe"


def test_no_install_without_an_installer_and_its_checksum(monkeypatch):
    monkeypatch.setattr(updates, "installed", lambda: True)
    monkeypatch.setattr(updates.os, "name", "nt")
    monkeypatch.setattr(updates, "platform_kind", lambda: "exe")
    u = Updater()
    u.releases = newer_releases([release("v9.0.0", sha=False)], "3.0.0", "exe")
    assert u.state()["available"] and not u.state()["canInstall"]
    u.releases = newer_releases([release("v9.0.0")], "3.0.0", "exe")
    assert u.state()["canInstall"]


def test_a_copy_run_from_source_never_installs(monkeypatch):
    monkeypatch.setattr(updates, "installed", lambda: False)
    monkeypatch.setattr(updates, "platform_kind", lambda: "exe")
    u = Updater()
    u.releases = newer_releases([release("v9.0.0")], "3.0.0", "exe")
    assert u.state()["available"] and not u.state()["canInstall"]
    assert u.start_install(on_ready=lambda: None) is False


class FakeResponse:
    def __init__(self, data: bytes):
        self.data = data
        self.text = data.decode("latin-1")
        self.headers = {"content-length": str(len(data))}

    def raise_for_status(self):
        pass

    def iter_bytes(self, n):
        for i in range(0, len(self.data), n):
            yield self.data[i : i + n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_client(files: dict[str, bytes]):
    class Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return FakeResponse(files[url])

        def stream(self, method, url):
            return FakeResponse(files[url])

    return Client


def run_install(monkeypatch, tmp_path, checksum: str):
    import httpx

    from tarjuman import config

    payload = b"MZ installer bytes" * 1000
    files = {
        "https://x/Tarjuman-Setup-9.0.0.exe": payload,
        "https://x/Tarjuman-Setup-9.0.0.exe.sha256": f"{checksum}  Tarjuman-Setup-9.0.0.exe\n".encode(),
    }
    started, ready = [], []
    monkeypatch.setattr(httpx, "Client", fake_client(files))
    monkeypatch.setattr(updates.subprocess, "Popen", lambda args, **k: started.append(args))
    monkeypatch.setattr(updates, "READY_DELAY", 0)
    monkeypatch.setattr(updates, "installed", lambda: True)
    monkeypatch.setattr(updates.os, "name", "nt")
    monkeypatch.setattr(updates, "platform_kind", lambda: "exe")
    monkeypatch.setattr(config, "TMP", tmp_path)
    u = Updater()
    u.releases = newer_releases([release("v9.0.0")], "3.0.0", "exe")
    assert u.start_install(on_ready=lambda: ready.append(True))
    for _ in range(200):
        if u.phase in ("error",) or ready:
            break
        time.sleep(0.02)
    return u, payload, started, ready


def test_a_verified_download_is_started_and_the_app_asked_to_close(monkeypatch, tmp_path):
    good = hashlib.sha256(b"MZ installer bytes" * 1000).hexdigest()
    u, payload, started, ready = run_install(monkeypatch, tmp_path, good)
    assert ready == [True] and u.phase == "starting" and u.progress == 100
    assert started and started[0][0].endswith("Tarjuman-Setup-9.0.0.exe") and "/SILENT" in started[0]
    assert (tmp_path / "update" / "Tarjuman-Setup-9.0.0.exe").read_bytes() == payload


def test_a_download_that_does_not_match_its_checksum_is_never_started(monkeypatch, tmp_path):
    u, _payload, started, ready = run_install(monkeypatch, tmp_path, "0" * 64)
    assert u.phase == "error" and "checksum" in u.message
    assert started == [] and ready == []
    assert not list((tmp_path / "update").glob("*.exe")), "the bad file is removed"


def test_the_linux_appimage_replaces_itself_after_a_verified_download(monkeypatch, tmp_path):
    import httpx

    payload = b"ELF new appimage" * 500
    running = tmp_path / "Tarjuman-3.0.0-x86_64.AppImage"
    running.write_bytes(b"old appimage")
    files = {
        "https://x/Tarjuman-9.0.0-x86_64.AppImage": payload,
        "https://x/Tarjuman-9.0.0-x86_64.AppImage.sha256": (hashlib.sha256(payload).hexdigest() + "  x\n").encode(),
    }
    monkeypatch.setattr(httpx, "Client", fake_client(files))
    monkeypatch.setattr(updates, "platform_kind", lambda: "appimage")
    monkeypatch.setenv("APPIMAGE", str(running))
    started = []
    monkeypatch.setattr(updates.subprocess, "Popen", lambda args, **k: started.append(args))
    u = Updater()
    u.releases = newer_releases([release("v9.0.0", appimage=True), release("v8.0.0")], "3.0.0", "appimage")
    assert [(r["version"], bool(r["installer"])) for r in u.releases] == [("9.0.0", True), ("8.0.0", False)], (
        "every newer release shows its notes; on Linux only the AppImage counts as a download"
    )
    assert u.state()["canInstall"] and u.state()["kind"] == "appimage"
    assert u.start_install(on_ready=lambda: None)
    for _ in range(200):
        if u.phase in ("restart", "error"):
            break
        time.sleep(0.02)
    assert u.phase == "restart", u.message
    assert running.read_bytes() == payload and started == [], "replaced in place; no installer is run"
    assert sorted(p.name for p in tmp_path.iterdir()) == [running.name], "nothing left beside it"


def test_without_a_writable_appimage_linux_only_shows_the_page(monkeypatch):
    monkeypatch.setattr(updates, "platform_kind", lambda: "appimage")
    monkeypatch.delenv("APPIMAGE", raising=False)
    u = Updater()
    u.releases = newer_releases([release("v9.0.0", appimage=True)], "3.0.0", "appimage")
    assert u.state()["available"] and not u.state()["canInstall"]
