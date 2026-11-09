# Tarjuman privacy policy

*Last updated: 9 November 2026*

Tarjuman is a browser extension and a free, open-source app that shows translated subtitles and an optional dubbed voice on videos. This policy covers the extension ("Tarjuman — Arabic subtitles & dubbing for any video") and the Tarjuman app it works with.

## The short version

- The extension talks **only to the Tarjuman app on your own computer** (`127.0.0.1` / `localhost`).
- There is **no account, no analytics, no advertising and no tracking**. The developer receives nothing.
- Your data is **never sold** or shared for any other purpose.

## What the extension processes, and where it goes

| What | When | Where it goes |
|---|---|---|
| The address of the video you are watching | When you start translation | Your local Tarjuman app, so it can fetch that video's captions |
| The captions shown in a site's own video player | When you start translation on a site that has them | Your local Tarjuman app, to translate them |
| The audio of the tab | Only in live mode (a site without captions), after you start it | Your local Tarjuman app, to transcribe and translate it. The extension also plays the tab's sound back to you, because the browser mutes a tab while it is captured |
| Your settings (language, subtitle style, voice) | Always | Stored in your browser (`chrome.storage`). They are not synced or sent anywhere |
| Which tab is being translated | While translation is on | Stored in your browser for the current session only |

The extension does not read pages you don't translate, does not record your browsing, and keeps no history.

## What the local Tarjuman app may contact

The Tarjuman app runs on your computer and does the actual work. To do it, it may contact these services directly from your computer:

- **YouTube** — to read a video's captions and details, and to download audio or video when you ask it to transcribe or dub a video.
- **Google Translate** and **MyMemory** — to translate caption text. Only the text being translated is sent.
- **Microsoft Edge text-to-speech voices** — to synthesize the dubbed voice. Only the sentence being spoken is sent. (An offline voice, Piper, is used when it is installed or when the online voices are unavailable.)
- **An AI provider you configure yourself (optional)** — for example Anthropic (Claude) or an OpenAI-compatible service, only if you enter your own API key in the app's settings. Then the caption text of the videos you choose to process with AI is sent to that provider. Your key stays on your computer and is never shown back or sent anywhere else.
- **Sites you give the app a link to** — when you ask the app to download a video from another site.

Each of these services has its own privacy policy. Speech recognition (Whisper) runs entirely on your computer.

The app stores its cache (translations, synthesized voice files), your corrections and your files in its own `data/` folder on your computer. You can delete that folder at any time.

## Permissions

The extension asks only for what it needs: storage for settings, temporary access to the current tab when you click it (`activeTab`), the ability to show the subtitle overlay (`scripting`), and audio capture for live mode (`tabCapture`, `offscreen`). It can reach only `127.0.0.1` and `localhost`. On sites other than YouTube it asks you for that one site, and you can remove sites at any time in the extension's settings.

## Children

Tarjuman is a general-purpose tool and does not knowingly collect any information from anyone, including children.

## Changes

If this policy changes, the new version will be published at this address with a new date. Material changes will be noted in the extension's release notes.

## Contact

Questions or concerns: open an issue at <https://github.com/MohamedElnagar94/tarjuman/issues>.
