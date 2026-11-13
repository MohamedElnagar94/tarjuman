# Tarjuman — specification

This document is the contract between the backend, the web app and the extension. If code and spec disagree, fix one of them in the same commit.

## 1. Repository layout

```
tarjuman/
├─ backend/                 Python 3.11+ package `tarjuman` (FastAPI)
│  ├─ tarjuman/
│  │  ├─ __main__.py        CLI: serve | subs <url> | setup | update | doctor
│  │  ├─ config.py          paths, ports, env vars
│  │  ├─ core/              errors, HTTP client, JSON stores, text helpers
│  │  ├─ captions/          YouTube InnerTube, caption parsing, repair, formats
│  │  ├─ translate/         Google gtx, MyMemory, cache, user edits
│  │  ├─ voice/             voice catalogue, engines, priority gate, TTS cache, pronunciation
│  │  ├─ dub/               sentence grouping, pacing, live dub plans
│  │  ├─ ai/                Claude + OpenAI-compatible client, script writer, summary, Q&A
│  │  ├─ media/             local media library, yt-dlp, ffmpeg, mixer, separator, pitch
│  │  ├─ jobs/              job manager + whisper / dub / subvideo / batch / fetch jobs
│  │  ├─ learn/             vocabulary
│  │  └─ api/               FastAPI app, security, routes
│  └─ tests/
├─ shared/dub-engine/       the live dub engine (ES module), used by the web app and the extension
├─ frontend/                Vue 3 + Vite + TypeScript web app (served by the backend)
├─ extension/               Chrome/Edge MV3 extension (Vue 3 + Vite)
├─ assets/brand/            logo and icon sources
├─ docs/                    plan, specs, implementation notes, translated READMEs, screenshots
└─ scripts/                 build helpers (icons, screenshots, packaging)
```

## 2. Runtime

- `python -m tarjuman` starts the server on `127.0.0.1`/`0.0.0.0`, port **4318**. If that port is taken it tries the next one, up to 4327. The extension probes that range.
- Data lives in `data/` under the project root. Set `TARJUMAN_HOME` to move it.

```
data/
├─ cache/translations.json   translation cache  {"<tl>|<text>": "<translation>"}
├─ cache/edits.json          user corrections   {"<tl>|<src>": "<translation>"}  (they always win)
├─ cache/tts/<sha1>.mp3|wav  synthesized sentences, plus _meta.json {durations, cps}
├─ cache/ai-script.json      AI dub lines
├─ settings.json             AI provider settings (0600, written atomically)
├─ vocab.json, pronounce.json
├─ output/                   subtitle files
├─ output/dubbed/            dubbed and subtitled MP4s
├─ output/media/             uploaded and downloaded videos + media.json
├─ models/                   Piper voice, MDX-Net separator, Hugging Face cache (Whisper)
└─ tmp/                      job work directories (deleted when the job ends)
```

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `TARJUMAN_HOME` | project root | where `data/` lives |
| `TARJUMAN_PORT` | 4318 | first port to try |
| `TARJUMAN_HOST` | 0.0.0.0 | `127.0.0.1` keeps it to this computer only |
| `TARJUMAN_WHISPER_MODEL` | base | faster-whisper model |
| `TARJUMAN_FORCE_ASR` | 0 | prefer YouTube auto-captions over manual ones |
| `ANTHROPIC_API_KEY` | – | used when the settings hold no key |

## 3. Security rules (all `/api/*` routes)

1. **Host check.** The `Host` header must be `localhost`, an IPv4 address or an IPv6 address. This blocks DNS rebinding.
2. **Origin check.** Requests from `chrome-extension://`, `moz-extension://` and `edge-extension://` origins are allowed. Any other `Origin` must equal the request host. With no `Origin`, the request is rejected if `Sec-Fetch-Site: cross-site`.
3. **JSON only.** `POST` requires `Content-Type: application/json`. The one exception is `POST /api/media/upload`, which takes `application/octet-stream`. HTML forms on other sites can't send either without a CORS preflight.
4. **Local only.** `/api/settings` and `/api/ai/test` answer only to loopback clients, because the settings hold an API key.
5. **Pairing.** A client that isn't loopback (a phone on the Wi-Fi) gets `401 {code:"NOT_PAIRED"}` on every route except `/api/health` until it is paired. It is paired by opening `/pair?code=<invite>` once (the QR in Settings → Phone, also printed at startup). Each device gets its own key in the HttpOnly cookie `tarjuman_pair`; only its SHA-256 is stored, with a name from the User-Agent, `pairedAt`, `lastSeen` and `lastIp`. One invite pairs any number of devices. It lasts `TARJUMAN_PAIR_MINUTES` (default 15, `0` = until replaced): after that `/pair` answers 403 and Settings shows a new one (`codeExpires`, in ms, is part of the pairing state). Five wrong codes from one address within ten minutes get `429` until the ten minutes pass. `GET /api/pairing` lists them; `POST /api/pairing/device {id, action:"remove"|"rename", name}` unpairs or renames one; `POST /api/pairing/reset` makes a new invite (the old QR stops working, paired devices stay); `POST /api/pairing/unpair-all` unpairs every device and makes a new invite. Every `/api/pairing*` route is local only. A device paired by the first version (one shared secret) is moved to its own key on its next request.
6. **Extensions.** The first extension origin that connects is trusted. Any other gets `403 {code:"EXTENSION_NOT_ALLOWED"}` until it is allowed (`GET /api/extensions`, `POST /api/extensions/set {id, allow}`, both local only). `/api/health` still answers it, with `extensionAllowed:false`.
7. **Uploads** are capped at `TARJUMAN_MAX_UPLOAD_GB` (default 8): `413 UPLOAD_TOO_LARGE`. They also stop before less than 1 GB would be left free on the disk: `507 DISK_FULL`. When the free space can't be measured the upload is refused too. A refused upload leaves no file behind.
8. The API key is never returned. Responses carry `hasKey` and `keyHint` (`…abcd`) instead. Changing the provider or `baseUrl` clears the stored key, so a key is never sent to a server it wasn't entered for.

Rejected requests get `403 {"ok":false,"code":"FORBIDDEN_ORIGIN"|"LOCAL_ONLY"}` or `415 {"ok":false,"code":"JSON_REQUIRED"}`.

## 4. Conventions

- Every JSON response has `ok: boolean`. On failure it also has `code` (a stable machine string) and `message` (human text).
- A failure that isn't the client's fault still answers **HTTP 200** with `ok:false`, as the prototype did and both clients expect. 4xx is used only for malformed requests and the security rules.
- Times are in seconds, as floats.
- A **link** is a YouTube URL or ID, or `media:<12 hex>` for a video in the local library.
- Language codes are normalised to their primary subtag (`ar-EG` → `ar`).

**Downloads** (`/api/media/fetch`, `/api/batch`) take only `http(s)` links whose host resolves to public addresses, checked again on each redirect (up to 5): a link to this computer, the local network, link-local or reserved ranges gets `URL_NOT_ALLOWED`. `TARJUMAN_FETCH_PRIVATE=1` turns this off, for a media server at home. The check runs before yt-dlp starts; requests yt-dlp makes later on its own are not inspected.

**Desktop app (Windows).** `GET /api/desktop` answers `{available, supported, settings:{minimizeToTray, closeToTray, startWithWindows, keepEngine}}`; `available` is true when the server runs inside the desktop app (`python -m tarjuman app`), where the settings take effect. `POST /api/desktop` changes any of them; `startWithWindows` adds or removes the value `Tarjuman` under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` at once. `POST /api/desktop/show` brings the app window up (a second start of the app sends it and exits). `POST /api/desktop/open {url}` opens an `http(s)` page in the user's default browser, since the app window is a browser profile of its own. All four are local only.

**Updates.** `GET /api/update[?force=1]` answers `{current, latest, available, releases:[{version, notes, date, page}], canInstall, installed, checkedAt, error, phase, progress, message, settings:{checkUpdates, autoUpdate}}`. It asks GitHub (`/repos/MohamedElnagar94/tarjuman/releases`) at most every six hours, and not at all when `checkUpdates` is off unless forced. `POST /api/update/install {force?}` downloads the newest installer, refuses it unless it matches the release's `.sha256` file, starts it silently and closes the desktop app; the installer starts the app again. It answers `JOBS_RUNNING` while jobs run (unless `force`), `UPDATE_NEEDS_APP` outside the desktop app, and `UPDATE_UNAVAILABLE` when there is nothing to install. Both are local only.

**Protocol version.** `/api/health` includes `api` (now `1`). It is raised only for a change that breaks an older client; a client built for a lower number should ask the user to update.

An unexpected failure answers `500 {ok:false, code:"ERROR", message, ref}`. The message is generic; the exception itself is only in the server log, next to the same `ref`.

### Error codes

`NOT_PAIRED`, `EXTENSION_NOT_ALLOWED`, `UPLOAD_TOO_LARGE`, `DISK_FULL`, `BAD_URL`, `URL_NOT_ALLOWED`, `QUEUE_FULL`, `NO_CAPTIONS`, `UNPLAYABLE`, `CAPTIONS_EMPTY`, `NO_MEDIA`, `NO_SPEECH`, `NO_JOB`, `NO_FILE`, `NO_TEXT`, `NO_CUES`, `NO_AUDIO`, `NO_WORD`, `NO_QUESTION`, `EMPTY_FILE`, `BAD_JSON`, `BODY_TOO_LARGE`, `CANCELLED`, `PY_NOT_INSTALLED`, `WHISPER_NOT_INSTALLED`, `TTS_ERROR`, `TTS_FAILED`, `TRANSLATE_FAILED`, `FFMPEG_NOT_FOUND`, `YTDLP_FAILED`, `DOWNLOAD_FAILED`, `MIX_FAILED`, `BURN_FAILED`, `PLAYLIST_FAILED`, `PLAYLIST_EMPTY`, `AI_NOT_READY`, `AI_AUTH`, `AI_RATE_LIMIT`, `AI_HTTP`, `AI_NETWORK`, `AI_REFUSED`, `AI_TRUNCATED`, `AI_SDK_MISSING`.

## 5. Data shapes

```ts
type Cue = { start: number; end: number; src: string; ar: string }   // `ar` = target-language text, any language

type VideoCues = {
  ok: true
  videoId: string            // 11-char YouTube id, or "media:<id>"
  title: string; author: string; lengthSeconds: number
  tl: string                 // target language
  alreadyTranslated: boolean // the target track came from YouTube
  autoTranslated?: boolean   // ...and it is YouTube's machine translation
  asr: boolean               // source is auto-generated speech recognition
  whisper?: boolean; media?: boolean
  srcLang: string
  cues: Cue[]
}

type Voice = { id: string; name: string; accent: string; gender: "m" | "f"; engine: "edge" | "piper" }

type DubBlock = {             // one spoken sentence of the live dub plan
  i: number                  // stable index within the video
  start: number              // when the engine should start speaking it
  slot: number               // seconds available until the next sentence
  rate: number               // pacing in % (-30..80) relative to the voice's natural speed
  synthRate: number          // rate to request from /api/tts (audio is pre-generated at this rate)
  playRate: number           // browser playbackRate correction (0.85..1.2)
  text: string               // what is spoken
  src: string                // source sentence
  srcStart: number; end: number
}

type Job = {
  ok: true; id: string
  type: "whisper" | "dub" | "subvideo" | "batch" | "fetch"
  status: "queued" | "running" | "done" | "error" | "cancelled"
  phase: string              // human-readable step, in Arabic
  progress: number           // 0..100
  message: string; title: string; videoId: string; startedAt: number /* ms */
  size: number; fileName: string; fileUrl: string   // fileUrl only when done and an MP4 exists
  dubInfo: object | null
  what?: "subs" | "subvideo" | "dub"
  items?: { id: string; title: string; status: string; message: string }[]  // batch only
}

type MediaItem = { id: string; link: string; title: string; source: string; created: number; size: number; transcribed: boolean }
type LibraryItem = { kind: "dubbed" | "subs"; name: string; size: number; mtime: number }
type VocabItem = { id: string; word: string; tr: string; sentence: string; sentenceTr: string; videoId: string; title: string; t: number; at: number }
type PronounceRule = { from: string; to: string }
```

## 6. HTTP API

| Method & path | Input | Output |
|---|---|---|
| `GET /api/health` | – | `{ok, app:"tarjuman", version, port, cache, providers, python, ffmpeg, whisper:{installed,ready,model,error}, tts:{installed,ready,edge,piper,stats}, ai:{ready,provider,model,style}, jobs}` |
| `GET /api/cues` | `url, tl=ar, fresh=0\|1` | `VideoCues` |
| `POST /api/translate` | `{texts[≤200], sl="auto", tl="ar"}` | `{ok, map:{text: translation}}`. Texts that failed are left out. |
| `POST /api/translate/edit` | `{src, ar, tl}` (empty `ar` removes the edit) | `{ok}` |
| `GET /api/subs` (alias `/api/srt`) | `url, tl, mode=ar\|bi\|src, format=srt\|vtt\|txt, save=0\|1` | the file as an attachment (UTF-8 with BOM, except VTT) |
| `GET /api/voices` | `lang` | `{ok, voices: Voice[]}`. The first voice is the default. |
| `GET /api/tts` | `text(≤1500), lang, voice, rate` | audio bytes, with headers `X-Audio-Duration` and `X-TTS-Engine` |
| `GET /api/dubplan` | `url, tl, voice, from, to, urgent=0\|1, speed=1` (the video's playback speed) | `{ok, from, to, total, end, blocks: DubBlock[]}` |
| `POST /api/dubplan/cues` | `{cues:[{start,end,src}], sl, tl, voice, from, to, urgent}` | the same as above, for captions taken from any website |
| `POST /api/whisper/job` | `{url, tl}` | `{ok, id}` |
| `GET /api/whisper/job` | `id` | `Job & {srcLang, tl, cues?}` (`cues` once done) |
| `POST /api/dub` (alias `/api/dub/job`) | `{url, lang, voice="auto", matchVoice, bgVolume=0.15, embedSubs=true, burnSubs=false, removeVoice=false, quality=480\|720\|1080}` | `{ok, id}` |
| `GET /api/dub/job` (alias `GET /api/dub`) | `id` | `Job` |
| `GET /api/dub/file` | `id, dl=0\|1` | MP4, with HTTP Range support |
| `POST /api/subvideo` | `{url, tl, mode=ar\|bi, quality}` | `{ok, id}` |
| `POST /api/batch` | `{url, what=subs\|subvideo\|dub, tl, limit≤200, voice, quality, bgVolume, embedSubs}` | `{ok, id}` |
| `POST /api/job/cancel` | `{id}` | `{ok}` |
| `GET /api/jobs` | – | `{ok, jobs: Job[]}`, newest first |
| `GET /api/library` | – | `{ok, items: LibraryItem[]}` |
| `GET /api/library/file` | `kind, name, dl` | the file (with Range support) |
| `POST /api/library/delete` | `{kind, name}` | `{ok}` |
| `POST /api/media/upload` | `?name=<file name>`, raw body as `application/octet-stream` | `{ok} & MediaItem` |
| `POST /api/media/fetch` | `{url}` (any site yt-dlp supports) | `{ok, id}`, a `fetch` job |
| `GET /api/media/job` | `id` | `Job & {media: MediaItem \| null}` |
| `GET /api/media` | – | `{ok, items: MediaItem[]}` |
| `GET /api/media/info` | `id` | `{ok} & MediaItem` |
| `GET /api/media/file` | `id` | the video, with Range support |
| `POST /api/media/delete` | `{id}` | `{ok}` |
| `POST /api/live` | `{audio_b64 (s16le mono 16 kHz), tl, tts, voice}` | `{ok, text, ar, lang, audio_b64, audio_mime}` |
| `GET/POST /api/vocab` | `POST {word, tr, sentence, sentenceTr, videoId, title, t}` | `{ok, items}` / `{ok, item, duplicate}` |
| `POST /api/vocab/delete` | `{id}` | `{ok}` |
| `GET /api/vocab.csv` | – | an Anki CSV |
| `GET/POST /api/pronounce` | `POST {items: PronounceRule[]}` | `{ok, items}` |
| `POST /api/pronounce/preview` | `{text}` | `{ok, text}` |
| `GET/POST /api/settings` 🔒 | `POST {ai:{enabled, provider:"anthropic"\|"openai", model, baseUrl, style:"msa"\|"egyptian", apiKey?: string\|null}}` | `{ok, ai:{enabled, provider, model, baseUrl, style, hasKey, keyHint, defaultModel, ready, stats}}` |
| `POST /api/ai/test` 🔒 | – | `{ok, text, ms, model}` |
| `POST /api/ai/summary` | `{url, tl}` | `{ok, summary, points[], chapters:[{start,title}]}` |
| `POST /api/ai/ask` | `{url, tl, question}` | `{ok, answer, moments: number[]}` |

🔒 = loopback clients only.

Everything else is served from the built web app (`frontend/dist`). Unknown paths fall back to `index.html` so the app's client-side routes work.

## 7. Live dubbing behaviour (shared engine)

These rules come from measurements on real videos in the prototype. Both clients depend on them.

1. **Sentences, not caption fragments.** Caption lines are merged into sentences: punctuation when the track has it, otherwise gaps over 0.9 s or a maximum length of 8 s (16 s with punctuation).
2. **Paragraph pacing.** Each sentence gets a rate from a rolling window of about 12 s inside its paragraph, where a gap of more than 1.2 s starts a new paragraph. Neighbouring sentences change speed gradually (+10% / −8% at most). Spare time slows the voice down to 0.92× rather than leaving silence. The dub is never more than 0.8 s behind the speaker, and the speed range is 0.92–1.5×.
3. **Measured, not estimated.** Before answering a plan request, the server synthesizes each sentence once at its estimated rate and measures it. It then returns `synthRate` (the audio already in cache) and `playRate` (a small browser correction, from 0.85 to 1.2).
4. **The engine never cuts or skips a sentence** because it is late. A late sentence plays faster: up to 1.3× extra, capped at 1.65× effective speed.
5. **Holding the video.** The video is paused only when the dub is more than 1.8 s behind, or when the next sentence's audio isn't ready 1.5 s after it was due. A hold never lasts longer than 15 s.
6. **Plan windows.** The first window is 12 s and later windows are 45 s. The engine keeps 60 s of plan and 40 s of audio ahead of playback, with up to 3 audio fetches in parallel.
7. **Seeking outside the prepared range** is treated as a fresh start. The engine holds the video at the new position, requests a small window marked `urgent`, and resumes from that exact spot. The TTS gate puts urgent work ahead of everything else, with these priorities: 3 for the spot just seeked to, 2 for play now, 1 for upcoming sentences and 0 for background warm-up.
8. **Never two voices at once.** Starting a sentence silences every other one.

## 8. Extension

- **Manifest V3.** Required permissions: `storage`, `activeTab`, `scripting`, `offscreen` and `tabCapture`. Host permissions are limited to `http://127.0.0.1/*` and `http://localhost/*`. YouTube is covered by a content script. `<all_urls>` is an **optional** host permission, requested when the user first turns translation on outside YouTube.
- **Modes.** `youtube` (the server's captions), `captions` (the site player's own text tracks, such as Coursera or Udemy), and `live` (tab audio → Whisper).
- **Pages.** The popup (quick controls), the options page (full settings), the welcome page (opened on install: how to start the local app) and the offscreen document (audio).
- **Strings** live in `_locales/en` and `_locales/ar`.
- **Shortcut.** `Alt+Shift+A` toggles translation in the current tab.
