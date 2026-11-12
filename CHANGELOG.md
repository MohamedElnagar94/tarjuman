# Changelog

Notable changes to Tarjuman. Versions follow the number in `backend/tarjuman/__init__.py`.

## 3.1.0 (2026-11-13)

### Desktop app (Windows)

- A notification-area icon, with Open, the engine's state, the extension's state, the data folder, and Quit.
- Settings → Desktop, four independent choices: minimize to the notification area, close to the notification area, start with Windows (in the notification area, without a window), and keep the engine running after the window closes, so the browser extension keeps working. Closing or quitting while jobs run asks first.
- Starting Tarjuman again brings up the running one instead of starting a second copy.
- Links to other sites open in your own browser, not inside the app window.
- Settings → Extensions has a button to get the extension from the Chrome Web Store.

### For developers

- `/api/health` reports the protocol version (`api`), for clients to check compatibility.
- Each release has a SHA-256 checksum file next to the installer.

## 3.0.0 (2026-11-11)

The first release of the rewrite: a Python backend, a Vue web app, a browser extension, and a Windows installer.

### Watching

- Synced, translated subtitles for YouTube videos, for videos from your computer, and for videos downloaded from other sites.
- Live dubbing that stays with the speaker: it follows the speaker's pauses, paces itself for the video's speed, and slows the video slightly instead of racing the voice.
- Videos without captions are transcribed on your computer with Whisper.
- Dubbed MP4 files, with the original speaker removed and the music kept, and videos with burned-in subtitles.
- Playlists and channels in one go.
- Arabic words that read two ways are diacritized from the meaning, so the voice says the right one.
- A summary of the video and questions about it, with the AI provider you choose (off by default).
- Saved words, with export to Anki.

### The browser extension

- Published on the [Chrome Web Store](https://chromewebstore.google.com/detail/gcfnomfbpenbhdebopmpdfamlaiodflp).
- Subtitles and dubbing on any site's video, including players inside an iframe from another site.
- Only the first extension that connects is trusted by itself; any other waits for your approval in Settings.

### Phone

- Open Tarjuman from a phone on the same Wi-Fi by scanning a QR code. Each phone gets its own key, is listed in Settings, and can be renamed or unpaired alone.
- The pairing code runs out after 15 minutes, and repeated wrong codes from one address are refused for a while.

### Windows

- An installer with its own Python, every package, the web app and the extension: neither Python nor Node.js is needed.
- Tarjuman opens in a window of its own (Edge or Chrome in app mode); closing the window stops it.
- Your data lives in `%LOCALAPPDATA%\Tarjuman`, apart from the program, so updates keep it.

### Safety and limits

- Requests from other websites are refused; devices other than your computer must be paired.
- Uploads have a size limit and stop before the disk is nearly full.
- Downloads refuse links that point into your local network.
- Heavy jobs (Whisper, dubbing, burning subtitles) share a limit, the waiting queue is bounded, and asking twice for the same download starts it once.
- An unexpected error shows a reference number; its details stay in the log.
- The saved dub voices are kept under a size limit.

### Settings and docs

- Settings can live in a `.env` file; `.env.example` explains each one in Arabic and English.
- Settings → Privacy lists what each feature sends, to whom, and the alternative that sends nothing.
- [Troubleshooting](docs/troubleshooting.md) covers the problems met so far and their fixes.

### For developers

- CI on GitHub Actions: backend on Linux and Windows, the dub engine, the web app, the extension, and browser tests of the main journeys against an offline server.
- A workflow that builds the Windows installer and attaches it to a release when a `v*` tag is pushed.
