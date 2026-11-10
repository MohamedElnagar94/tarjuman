# Chrome Web Store listing — English

## Name (max 75)

Tarjuman — Arabic subtitles & dubbing for any video

## Short description (max 132)

Synced Arabic subtitles and natural live dubbing on YouTube and any video site, powered by the Tarjuman app on your own computer.

*(129 characters. This is also the manifest `description`.)*

## Category

**Productivity** → *Tools*. (Alternative: *Education*, since most use is watching lectures and courses.)

## Language

English and Arabic (the listing, the extension UI and the overlay follow the browser language).

## Detailed description

Watch any video in Arabic.

Tarjuman puts synced Arabic subtitles on YouTube videos and on almost any other video site, and can dub the speaker with a natural Arabic voice in real time. Everything is processed by the free Tarjuman app running on your own computer; the extension is its remote control and display.

**What it does**

• YouTube — fetches the video's captions, translates them and shows them perfectly in sync. If a video has no captions, one click transcribes it with Whisper.
• Course sites (Coursera, Udemy and any player with its own subtitles) — translates the player's own captions, with the same exact timing.
• Any other video — listens to the tab's audio and shows live Arabic subtitles a few seconds behind the speaker.
• Live dubbing — the speaker talks in Arabic. Sentences are never cut off: a late sentence speaks a little faster, and the video waits a moment if it must. The original sound is lowered while the dub plays.
• Bilingual mode — the original line above the translation, for language learners.
• Your look — text size, position (top or bottom), background strength. Big, high-contrast subtitles that stay readable on any video, including in fullscreen.
• A small toolbar on the video (on hover) and the Alt+Shift+A shortcut.
• Other target languages: English, French, Spanish, German, Turkish.

**How to start**

1. Get the free Tarjuman app: https://github.com/MohamedElnagar94/tarjuman
2. Start it on your computer.
3. Open a video, click the Tarjuman icon, and press “Translate this video”.

**Private by design**

The extension talks only to the Tarjuman app on your own computer (127.0.0.1). There is no account, no analytics and no tracking, and the extension never sends your browsing to anyone. See the privacy policy for what the app itself contacts to translate and speak.

Tarjuman is free and open source.

## Single purpose

Tarjuman shows translated subtitles, and optionally a dubbed voice, on the video the user is watching, using the Tarjuman app that the user runs on their own computer.

## Permission justifications

| Permission | Justification |
|---|---|
| `storage` | Saves the user's preferences (target language, subtitle size, position and background, dubbing voice and options) and, per browser session, which tab is being translated, so translation survives the service worker being suspended. |
| `activeTab` | When the user clicks the toolbar button or presses the shortcut, gives temporary access to the current tab: to read its address (to tell YouTube from other sites), to show the subtitle overlay there, and to allow capturing its audio. No access is used without that user action. |
| `scripting` | Injects the subtitle overlay into the current tab on sites other than YouTube, only after the user starts translation there (with activeTab, or on a site the user chose to allow). |
| `offscreen` | Creates an offscreen document to capture the tab's audio for live subtitles on sites without captions, and to play the dubbed voice. A service worker cannot use audio APIs. |
| `tabCapture` | Captures the audio of the tab the user is translating, only on sites without captions and only after the user starts translation. The audio is sent to the user's own Tarjuman app on 127.0.0.1 for transcription and is played back to the user unchanged. |
| Host permission `http://127.0.0.1/*`, `http://localhost/*` | The local Tarjuman app the user runs on their own computer (ports 4318–4327). All requests go there: captions, translation, voices, live transcription. No other host is contacted by the extension. |
| Content script on `*://*.youtube.com/*` | Shows the synced subtitle overlay and runs the dub engine on YouTube video pages. It does nothing until the user starts translation. |
| Optional host permission `<all_urls>` | Never granted at install. When the user starts translation on a site other than YouTube for the first time, the extension asks for **that one site only** (for example `https://www.coursera.org/*`), plus the site of the embedded player when the video plays inside an iframe from another site (common on movie and anime sites), so the overlay can run inside the player and come back after the page reloads. The user may decline (translation then works until the page reloads), remove sites in the settings, or choose “Allow on all sites” there to stop being asked. |
| Web accessible resources (`fonts/*.woff2`) | The subtitle font, loaded by the overlay so Arabic text renders well on every site. No other extension file is exposed. |

## Remote code

**No, I am not using remote code.** All JavaScript, styles and fonts are bundled in the package. There is no `eval`, no remotely hosted script, no CDN.

## Data usage (Privacy practices tab)

The extension collects or transmits:

- **Website content** — *yes, locally only*: the text of the captions on the page, and when live mode is used, the tab's audio, are sent to the Tarjuman app on the user's own computer (127.0.0.1) to be translated. They are not sent to the developer or any server the developer controls.
- **Web history** — *no*. The address of the current video is sent only to the user's own local app, so it can fetch the captions.
- Personally identifiable information, health, financial, authentication, personal communications, location, user activity — **no**.

Certifications:

- [x] I do not sell or transfer user data to third parties, outside of the approved use cases.
- [x] I do not use or transfer user data for purposes that are unrelated to my item's single purpose.
- [x] I do not use or transfer user data to determine creditworthiness or for lending purposes.

Privacy policy URL: `https://mohamedelnagar94.github.io/tarjuman/privacy.html` (host `store/privacy.html` there).

## Assets

| Asset | File |
|---|---|
| Icon 128×128 | `public/icons/icon-128.png` |
| Small promo tile 440×280 | `store/promo/small-tile-440x280.png` |
| Marquee 1400×560 | `store/promo/marquee-1400x560.png` |
| Screenshots 1280×800 | `store/screenshots/` (see the README there) |
