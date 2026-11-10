<p align="center">
  <img src="assets/brand/icon-256.png" width="128" height="128" alt="Tarjuman icon: the Arabic letter taa under a play mark">
</p>

<h1 align="center">Tarjuman · ترجمان</h1>

<p align="center">
  <strong>Watch any video in Arabic.</strong><br>
  Synced translation, natural live dubbing, dubbed MP4s, and a browser extension. Everything runs on your own computer.
</p>

<p align="center">
  <a href="https://github.com/MohamedElnagar94/tarjuman/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MohamedElnagar94/tarjuman/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-3550D6"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-1F2E8C">
  <img alt="Vue 3" src="https://img.shields.io/badge/vue-3-1F2E8C">
  <img alt="Chrome MV3" src="https://img.shields.io/badge/chrome-MV3-F0922B">
</p>

<p align="center">
  <b>English</b> ·
  <a href="docs/i18n/README.ar.md">العربية</a> ·
  <a href="docs/i18n/README.fr.md">Français</a> ·
  <a href="docs/i18n/README.es.md">Español</a> ·
  <a href="docs/i18n/README.de.md">Deutsch</a> ·
  <a href="docs/i18n/README.it.md">Italiano</a> ·
  <a href="docs/i18n/README.pt.md">Português</a> ·
  <a href="docs/i18n/README.tr.md">Türkçe</a> ·
  <a href="docs/i18n/README.ru.md">Русский</a> ·
  <a href="docs/i18n/README.ur.md">اردو</a> ·
  <a href="docs/i18n/README.fa.md">فارسی</a> ·
  <a href="docs/i18n/README.hi.md">हिन्दी</a> ·
  <a href="docs/i18n/README.id.md">Bahasa Indonesia</a> ·
  <a href="docs/i18n/README.zh.md">中文</a> ·
  <a href="docs/i18n/README.ja.md">日本語</a> ·
  <a href="docs/i18n/README.ko.md">한국어</a>
</p>

<p align="center">
  <img src="docs/screenshots/watch.png" alt="Tarjuman playing a YouTube video with Arabic subtitles and the dub panel open" width="900">
</p>

## What it does

Paste a YouTube link, upload a video from your computer, or give it a link from almost any site.

- **Synced subtitles.** Arabic subtitles appear on the video line by line, with the original language underneath if you want it. Auto-generated captions are rebuilt into whole sentences before they are translated; when they have no punctuation at all, they are cut where the speaker actually pauses, using YouTube's per-word timings.
- **Live dubbing that sounds like a person.** A neural Arabic voice speaks each sentence in time with the speaker, in Egyptian, Saudi, Emirati, Syrian, Jordanian, Lebanese, Moroccan or Iraqi Arabic. A sentence is never cut off or skipped. With a fast speaker the video slows down slightly while the voice catches up, instead of the voice racing; slow the video yourself and the voice gets that extra time. Words that are spelled the same but read differently are read the way the sentence means (الجُمَل "sentences", not الجَمَل "the camel"), decided by the English original.
- **Dubbed MP4.** Export the video with the Arabic voice-over. It can remove the original speaker's voice while keeping the music and effects, give each speaker a matching male or female voice, and embed or burn in subtitles.
- **No captions? No problem.** Whisper transcribes the audio on your computer, then the transcript is translated.
- **Subtitle files.** Download SRT, VTT or plain text, in Arabic or bilingual, or a subtitled MP4 ready to share.
- **Whole playlists.** Give it a playlist or channel link to make subtitles, subtitled videos or dubbed videos for every video in it.
- **Ask the video** (optional AI). Get a summary, key points, clickable chapters, and answers that jump to the moment the video covers your question. Works with Claude or any OpenAI-compatible provider (Gemini, Groq, OpenRouter, Ollama).
- **Learn English.** Tap any word for its meaning, save it with its sentence, review it later, and export to Anki. You can also repeat a sentence, pause after each line, or blur the subtitles to test yourself.
- **Browser extension.** Use the same subtitles and dubbing on YouTube itself, on sites whose player has captions (Coursera, Udemy and others), on movie and anime sites that embed their player from another site, or on any other site by listening to the tab's audio.
- **On your phone.** Open the app from any phone on the same Wi-Fi.

Other languages work too: French, Spanish, German, Turkish and English are built in as targets.

## Screenshots

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/home.png" alt="Home: paste a link, upload a video, recent videos and the computer's status"></td>
    <td width="50%"><img src="docs/screenshots/watch-en.png" alt="Watching a video with synced subtitles and the transcript, in English and the light theme"></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/library.png" alt="My files: jobs, a playlist batch, uploaded videos and finished files"></td>
    <td><img src="docs/screenshots/settings.png" alt="Settings: AI provider, pronunciation dictionary, defaults and appearance"></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/extension-overlay.png" alt="The extension showing Arabic subtitles on YouTube"></td>
    <td><img src="docs/screenshots/extension-welcome.png" alt="The extension's welcome page, connected to the app"></td>
  </tr>
</table>

<p align="center">
  <img src="docs/screenshots/phone-home.png" alt="Home on a phone" width="260">
  <img src="docs/screenshots/phone-watch.png" alt="Watching on a phone" width="260">
</p>

## Quick start

You need **Python 3.11+** and **Node.js 20+**.

**Windows:** double-click `start.cmd`. If Windows asks whether to run a script from an unknown publisher, create a desktop shortcut once with `powershell -ExecutionPolicy Bypass -File scripts/create-shortcut.ps1` and start Tarjuman from it; it runs the same script through Windows' own `cmd.exe`, so the prompt doesn't appear.

**macOS / Linux:**

```sh
./start.sh
```

On Debian, Ubuntu and Kali, install `python3-venv` first if it is missing (`sudo apt install python3-venv`).

The first run installs everything: the Python packages, the offline Arabic voice, and a build of the web app. Then the app opens at `http://127.0.0.1:4318`. On later runs it starts in a couple of seconds. To use it from your phone, open the address it prints for your Wi-Fi. On Windows, if the phone can't reach it, run `scripts/allow-phone.ps1` once as administrator: it marks your home Wi-Fi as Private and opens Tarjuman's ports on Private networks only.

<details>
<summary>Manual setup</summary>

```sh
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt        # Windows: .venv\Scripts\pip
npm --prefix frontend install && npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python -m tarjuman           # Windows: set PYTHONPATH=backend
```

</details>

### Commands

| Command | What it does |
|---|---|
| `python -m tarjuman` | Start the app (`--port`, `--host 127.0.0.1` for this computer only, `--no-open`) |
| `python -m tarjuman subs <link>` | Write subtitle files to `data/output` (`--lang`, `--format srt,vtt,txt`) |
| `python -m tarjuman setup` | Install or repair everything |
| `python -m tarjuman update` | Update yt-dlp and the voice client, if downloads or voices stop working |
| `python -m tarjuman doctor` | Check every component |

## The browser extension

<p align="center">
  <img src="docs/screenshots/extension-popup.png" alt="The Tarjuman extension popup" width="320">
</p>

1. Build it once: `npm --prefix extension install && npm --prefix extension run build`.
2. Open `chrome://extensions` (or `edge://extensions`), turn on **Developer mode**, click **Load unpacked**, and choose `extension/dist`.
3. Keep the app running, open a video, and click the Tarjuman icon, or press <kbd>Alt</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd>.

The extension talks only to the app on your computer. Its Chrome Web Store kit (listing text, permission justifications, privacy policy, promo images) is in [`extension/store`](extension/store).

## How the dub stays in sync

Caption lines are merged into whole sentences and spoken filler is removed. Each sentence's speed is then chosen from a look-ahead window of about 12 seconds, so a roomy sentence lends time to a crowded one and the speed changes gradually instead of jumping. Before the browser plays the first sentences of each stretch, the server synthesizes and measures them, so the plan is based on real durations rather than guesses, and it prepares the next stretch in the background. If the dub still falls behind, the video slows to 85% of your speed until the voice catches up, and pauses only when the gap passes about two seconds. Pacing follows your playback speed. Seeking anywhere resumes the dub on the exact spot. When the free translators rate-limit, a second Google endpoint and then YouTube's own translation keep the dub talking.

The full design is in [docs/implementation.md](docs/implementation.md).

## Privacy

Tarjuman is local-first. Your videos, subtitles, saved words, settings and API key stay in the `data/` folder on your computer. The app contacts YouTube (captions and downloads), Google Translate and MyMemory (translation), Microsoft's Edge voice service (speech) and, only if you turn it on, the AI provider you choose. There are no accounts, analytics or tracking. The API refuses requests from other websites, and the AI settings can only be changed from the computer running the app.

## Configuration

| Environment variable | Default | Meaning |
|---|---|---|
| `TARJUMAN_HOME` | project folder | Where `data/` is kept |
| `TARJUMAN_PORT` | `4318` | First port to try (it moves up if the port is busy; the extension follows) |
| `TARJUMAN_HOST` | `0.0.0.0` | Use `127.0.0.1` to keep the app off your Wi-Fi |
| `TARJUMAN_WHISPER_MODEL` | `base` | `small` or `medium` for more accurate transcription (slower) |
| `TARJUMAN_VOICE_CACHE_GB` | `2` | Size limit of the saved dub voices; the least recently used are removed first |
| `TARJUMAN_MAX_UPLOAD_GB` | `8` | Largest video you can upload |
| `ANTHROPIC_API_KEY` | – | Used for Claude when no key is saved in the settings |

## Project layout

```
backend/     Python package `tarjuman` (FastAPI): captions, translation, voices, dubbing, AI, jobs
frontend/    Vue 3 + Vite + TypeScript web app
extension/   Chrome / Edge extension (Manifest V3, Vue + Vite) and its store kit
shared/      the live dub engine used by both the web app and the extension
assets/      brand (icon source and renders)
docs/        plan, specification, implementation notes, translated READMEs, screenshots
```

## Development

```sh
# backend tests (offline)
cd backend && ../.venv/bin/python -m pytest      # Windows: ..\.venv\Scripts\python

# dub engine tests
npm test

# web app with hot reload (proxies the API to 127.0.0.1:4318)
npm --prefix frontend run dev

# extension: build, test, package a store zip
npm --prefix extension run build && npm --prefix extension test && npm --prefix extension run package
```

Read [docs/specs.md](docs/specs.md) before changing an API route: the web app and the extension both depend on it.

## Built with

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) ·
[edge-tts](https://github.com/rany2/edge-tts) ·
[Piper](https://github.com/rhasspy/piper) ·
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ·
[Ultimate Vocal Remover's MDX-Net models](https://github.com/TRvlvr/model_repo) ·
[FastAPI](https://fastapi.tiangolo.com) ·
[Vue](https://vuejs.org) ·
[Claude](https://www.anthropic.com/claude)

## License

[MIT](LICENSE). Downloading videos and captions is subject to each site's terms. Use Tarjuman for content you are allowed to watch and adapt.
