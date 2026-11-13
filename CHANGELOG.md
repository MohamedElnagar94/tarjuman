# Changelog

Notable changes to Tarjuman. Versions follow the number in `backend/tarjuman/__init__.py`.

## Browser extension 3.0.1 (2026-11-13)

- Subtitle fonts: Plex (default), Cairo, Naskh, Amiri, Tajawal, Kufi or the system font (options page).
- Interface language: the browser's, Arabic or English, chosen in the options page.
- The welcome page's "Get the app" opens the Releases page with the Windows installer, and it stops checking for the app once it has found it.
- Live subtitles send the tab's audio as raw bytes (`/api/live/raw`), a third less than before; an app older than 3.1 still gets the old form.
- When the app on the computer is older than the extension, the popup says so, with a link to update it.

## 3.1.0 (2026-11-13)

### Desktop app (Windows)

- A notification-area icon, with Open, the engine's state, the extension's state, the data folder, and Quit.
- Settings → Desktop, four independent choices: minimize to the notification area, close to the notification area, start with Windows (in the notification area, without a window), and keep the engine running after the window closes, so the browser extension keeps working. Closing or quitting while jobs run asks first.
- Starting Tarjuman again brings up the running one instead of starting a second copy.
- Installing or uninstalling closes a running Tarjuman by itself (it is asked to quit first, so it saves its work); Setup no longer stops to list "Python" as an application in use.
- The app window has no address bar, so a microphone permission refused by mistake couldn't be given back: Tarjuman's own page is allowed the microphone each time the window opens.
- Links to other sites open in your own browser, not inside the app window.
- Settings → Extensions has a button to get the extension from the Chrome Web Store.

### Linux

- A Linux app: `Tarjuman-<version>-x86_64.AppImage` on the Releases page, one file with its own Python, packages, web app and extension. Data in `~/.local/share/Tarjuman`. It updates itself from Settings → Updates (restart to use the new version).

### Updates

- Settings → Updates shows when a newer version is out, with what each version added and fixed, and updates in one click: the installer is downloaded, checked against its SHA-256 file, and Tarjuman restarts updated. A small "Update available" badge appears in the header.
- Choices: check automatically (every few hours, on by default) and install automatically (off by default).

### Settings

- Words in your recordings are a table like the pronunciation dictionary: how a word should be written, and (optionally) how Whisper writes it wrong, which is then replaced after transcribing.
- With "minimize to the notification area" on, clicking the taskbar button minimizes the window to the taskbar as usual; only the window's own minimize button sends it to the notification area.
- Settings show one section at a time: pick it on the side (or along the top on a phone). The address keeps the section, so a link or a reload opens the same one.
- After an update the app window never keeps running an old script: the web app's files are checked for changes each time.

### Recordings

- Audio files (voice notes, lectures, podcasts, songs) open in a player of their own instead of an empty video frame: the sound drawn live behind the sentence being said, the whole recording as a waveform to click or drag through with its sentences marked under it, 5-second skips, previous/next sentence, speed and repeat-sentence. Every screen says "recording", not "video".
- Record with your microphone from the home page ("Record your voice"): the voice is drawn as it comes in; stop, and it is saved, transcribed and translated by itself.
- More formats: Opus, OGG, AAC, AMR, WMA, AIFF, CAF, M4B and more; a file is classed as audio or video by what it holds (an MP3 with cover art is audio, a WebM can be either). Browser recordings are repaired once so they show their length and can be seeked.
- Dubbing a recording gives an M4A of the same length; "subtitled video" turns it into a video of its moving waveform with the translation on it, to post where only video is accepted.
- The library shows recordings with a small waveform, their length and the Whisper model that transcribed them. "Transcribe again" redoes a file with the current settings.

### Transcription accuracy

- A model for each use, each "Automatic" by default from what this computer can do: recordings (accuracy first: the most accurate model for short ones), videos from this computer, YouTube or any site (balanced), and the extension's live captions (fast enough to keep up). With 12 GB of memory or more two models stay loaded, so moving between them needs no reload.
- Any Whisper model can be added (Settings -> Transcription -> Add another model): its Hugging Face name or a folder on this computer. It is checked before anything is downloaded (faster-whisper format, really Whisper, size and licence), with a plain reason when it can't be used, and pinned to the version that was checked.
- A new model, `large-v3-arabic`: Whisper large-v3 trained on Arabic dialects (Apache-2.0, pinned to a known version). On a real 36-second Egyptian voice note it got 29% of the words wrong without the words list and 24% with it, against 41% and 29% for large-v3. With the spoken language set to Arabic, Automatic uses it for short recordings.
- Settings → Transcription shows this computer (CPU threads, memory, NVIDIA card and whether CUDA can use it), the model it should use and why, and each model's Arabic accuracy, download size, speed on this computer and a warning when it is too heavy. A model can be downloaded and prepared ahead of time.
- "Automatic" gives short recordings (up to 2 minutes, like voice notes) the most accurate model the computer can hold (large-v3 with 12 GB of memory or more), and longer ones the faster recommended model. On a 36-second Egyptian voice note with names and English words, large-v3 got 29% of the words wrong against 45-50% for large-v3-turbo.
- Spoken language (automatic or fixed), how Arabic is written (general with punctuation, MSA, Egyptian, Gulf, Levantine, Maghrebi; given only to Arabic speech), beam search, audio cleanup for noisy recordings, and skipping silences.
- Long stretches of speech are cut into sentences by the time of each word, so each subtitle shows on time and "repeat sentence" repeats a sentence.
- On a graphics card that fails, transcription falls back to the CPU and says why. `TARJUMAN_WHISPER_MODEL` is now empty by default; the old default `base` no longer overrides the recommendation.

### Watching

- Subtitle fonts: Readex (default), Cairo, Naskh, Amiri, Tajawal, Kufi or the system font (Settings → Appearance).
- Speech already in the target language (an Arabic voice note watched in Arabic) is shown once per line and not sent for translation; the original line takes its own direction.

### For developers

- `/api/health` reports the protocol version (`api`), for clients to check compatibility.
- Each release has a SHA-256 checksum file next to the installer, and its notes come from this changelog.

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
