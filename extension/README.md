# Tarjuman browser extension

Chrome / Edge extension (Manifest V3) that puts synced Arabic subtitles, and optionally a live Arabic dub, on YouTube and almost any video site. It is the display and remote control for the **Tarjuman app**, which runs on the user's own computer and does all the work; the extension finds it on `http://127.0.0.1:4318`–`4327`.

## Build

Requires Node 20+. This folder is a standalone npm project.

```sh
npm install
npm run build      # type-check, then build into dist/
npm run dev        # rebuild on change (reload the extension in chrome://extensions after each build)
npm test           # unit tests for the pure helpers, locales and manifest
npm run package    # build, then zip dist/ (no source maps) → tarjuman-extension-<version>.zip
npm run promo      # re-render store/promo/*.png from scripts/promo/*.svg
npm run shots      # screenshots of the pages and overlay in a real Chrome (see store/screenshots/README.md)
```

The version comes from `package.json`. The manifest is generated from `src/manifest.ts`.

## Load unpacked

1. `npm run build`
2. Open `chrome://extensions` (or `edge://extensions`) and turn on **Developer mode**.
3. **Load unpacked** → choose `extension/dist`.
4. Start the Tarjuman app (`python -m tarjuman`). The welcome page that opens on install turns green when it finds it.

After rebuilding, press **Reload** on the extension card and refresh the video page.

## Publish

1. Bump `version` in `package.json`.
2. `npm run package`.
3. In the [Chrome Web Store developer dashboard](https://chrome.google.com/webstore/devconsole), upload `tarjuman-extension-<version>.zip`.
4. Fill the listing from `store/listing.en.md` (and add the Arabic listing from `store/listing.ar.md`): descriptions, category, single purpose, one justification per permission, "No" to remote code, and the data-usage answers.
5. Images: icon `public/icons/icon-128.png`, `store/promo/small-tile-440x280.png`, `store/promo/marquee-1400x560.png`, screenshots 1280×800.
6. Privacy policy URL: publish `store/privacy.html` (for example on GitHub Pages) and paste its address. `store/PRIVACY.md` is the same text in Markdown.

Edge Add-ons accepts the same zip.

## How it works

| Mode | Where | Source of the subtitles |
|---|---|---|
| `youtube` | YouTube | The app fetches the video's captions (`/api/cues`), the overlay syncs them to the player and translates any untranslated lines (`/api/translate`). No captions: a button transcribes the video with Whisper (`/api/whisper/job`). |
| `captions` | Sites whose player has text tracks (Coursera, Udemy, …) | The player's own track, read from the `<video>` element, translated the same way. Badge **CC**. |
| `live` | Any other video | The tab's audio (tabCapture → offscreen document), cut at natural pauses into 2.5–6 s phrases and sent to `/api/live`. Badge **LIVE**. |

Dubbing in the first two modes uses the shared engine `@tarjuman/dub-engine` (bundled from `../shared/dub-engine`) with `/api/dubplan` and `/api/tts`; in live mode the offscreen document plays the spoken translations in order.

Content scripts never call the server directly (page CORS and private-network rules would block them); everything goes through the service worker, which has host permission for loopback only.

### Source layout

```
src/
  background/   service worker: server discovery, start/stop, modes, badge, tab and permission events
  content/      the overlay (shadow DOM): subtitles, toolbar, YouTube/site-captions sync, Whisper offer, dub engine
  offscreen/    tab audio capture, chunking, /api/live, live dub playback
  popup/        quick controls (Vue)
  options/      all settings, sites, server address, shortcut (Vue)
  welcome/      onboarding, opened on install (Vue)
  ui/           shared Vue components, design tokens and bundled fonts
  shared/       pure helpers (settings, server discovery, cues, audio chunking, i18n, messages)
  manifest.ts
public/
  _locales/en, _locales/ar   every UI string
  icons/
scripts/        build, package, promo rendering, screenshots
store/          listing texts, privacy policy, promo images, screenshots
test/           vitest
```

## Permissions

| Permission | Why |
|---|---|
| `storage` | Settings, and which tab is translating (the service worker is suspended when idle). |
| `activeTab` | Clicking the toolbar button or pressing the shortcut grants access to the current tab: its URL (to tell YouTube from other sites), injecting the overlay, and capturing its audio. This is what lets the extension work on any site without asking for broad host access. |
| `scripting` | Injects the overlay on sites other than YouTube, after the user starts translation. |
| `offscreen` | A hidden document for audio capture and playback; service workers have no audio APIs. |
| `tabCapture` | Live mode: the tab's audio, only after the user starts translation on a site without captions. |
| Host `http://127.0.0.1/*`, `http://localhost/*` | The local Tarjuman app (match patterns cover every port). Nothing else is contacted. |
| Content script `*://*.youtube.com/*` | The overlay on YouTube, so it survives YouTube's in-page navigation and page reloads with no extra permission. |
| Optional host `<all_urls>` | Never granted at install. See below. |
| Web accessible `fonts/*.woff2` | The subtitle font. `@font-face` doesn't work inside a shadow root, so it is declared on the page; extension URLs are exempt from the page's CSP. |

There is no `tabs` permission: with `activeTab`, `chrome.tabs.query` still returns the active tab with its URL after the user clicks the extension, and content scripts report their own URL.

### Sites other than YouTube

`activeTab` + `scripting` + `tabCapture` are enough to translate any site **for the current page** after a click. They are not enough after the page reloads or navigates, because the activeTab grant ends then. So the first time the user starts translation on a site, the popup asks for that one origin (`chrome.permissions.request({ origins: ["https://site/*"] })`, which is inside the optional `<all_urls>`):

- **Allowed** → after a reload the service worker re-injects the overlay and translation carries on.
- **Declined** → translation still starts (activeTab) and stops cleanly at the next reload. The popup offers "Keep it on for this site" and doesn't ask again on every click.

The options page lists the allowed sites (with Remove) and has an "Allow on all sites" switch that requests `<all_urls>` for users who don't want to be asked per site. The permission prompt can close the popup; the service worker then finishes the start itself (`permissions.onAdded` + a pending-start note).

## Localization

All strings are in `public/_locales/{en,ar}/messages.json`; the manifest uses `__MSG_…__`. The popup, options, welcome page and overlay controls follow the browser language and switch to RTL in Arabic. Subtitle direction follows the *target* language. A unit test checks that both locales have the same keys and that every key used in the code exists.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Not running" in the popup | Start the Tarjuman app. Advanced: set a fixed address in Settings → Connection. |
| "Live translation needs Whisper" | `python -m tarjuman setup` |
| "The browser doesn't let extensions run on this page" | `chrome://` pages and the extension stores can't be scripted by any extension. |
| No subtitles on a site with DRM | Some sites block tab audio capture. |
| Translation stopped after a reload on a site | Allow the site (popup or Settings → Sites). |
