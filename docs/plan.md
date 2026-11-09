# Tarjuman — rewrite plan

Tarjuman (ترجمان, "the interpreter") is the rewrite of the `youtube-arabic` prototype. That prototype was one 4,000-line Node server, one 2,400-line HTML page, and a hand-written browser extension. It worked well, but it was hard to change. This rewrite keeps every feature and every timing behaviour we measured on real videos. What changes is the structure: a Python backend split into modules, a Vue web app, a Vue/Vite extension that can be published to the Chrome Web Store, and one dub engine that both clients share.

## Goals

1. **The same product, but maintainable.** Every module has one job, and every important behaviour has a test.
2. **Python end to end on the server.** Whisper, Edge TTS, Piper, yt-dlp, the MDX-Net vocal remover and the mixer were already Python. They now run in one Python process (or in subprocesses of it) instead of being driven by a Node server over JSON pipes.
3. **A web app that reads as a product, not a demo.** Vue 3, a clear information architecture, an Arabic-first RTL layout with English available, and accessibility built in.
4. **An extension that is ready for the Chrome Web Store.** Minimal permissions, localized `_locales`, an onboarding page, an options page, a privacy policy and the store listing assets.
5. **Documentation people can use.** An English README, translated READMEs, and a spec and implementation notes for contributors.

## Non-goals

- Cloud hosting or user accounts. Tarjuman stays local-first: your files, keys and cache never leave your computer, apart from the translation, voice and AI providers you call.
- Voice cloning. We tried it in the prototype and the result sounded unnatural, so the neural Edge voices remain the default.

## Phases

Each phase ends in one or more commits that build and pass their tests.

| # | Phase | Output |
|---|-------|--------|
| 0 | Scaffold | repo, `.gitignore`, plan, specs |
| 1 | Backend core | config, HTTP helpers, JSON stores, captions (InnerTube, parsing, ASR repair, roll-up unrolling, alignment), subtitle formats |
| 2 | Translation | Google gtx batching, MyMemory fallback, cache, user edits |
| 3 | Voice | voice catalogue, Edge/Piper/Google engines, the priority gate, the disk cache with measured durations, the pronunciation dictionary |
| 4 | Dub planner | sentence grouping, filler condensing, paragraph pacing, measured-duration planning |
| 5 | AI | Claude (official SDK) and OpenAI-compatible providers, script writer, summary and chapters, Q&A |
| 6 | Media and jobs | job manager with cancellation, yt-dlp downloads, uploads, Whisper, dubbed MP4, burned subtitles, batch playlists, vocal separation |
| 7 | HTTP API | FastAPI app, security middleware, all routes, static hosting of the web app |
| 8 | Shared dub engine | ES module plus tests (seek, hold, catch-up, no skips) |
| 9 | Web app | Vue 3 + Vite + TypeScript, i18n (ar/en), every feature of the prototype |
| 10 | Extension | MV3 on Vite: background, content overlay, offscreen capture, popup, options, welcome page, `_locales`, store assets |
| 11 | Brand and docs | icon set, README with icon, translated READMEs, implementation notes |
| 12 | Ship | screenshots, GitHub repository, push |

## Risks and how we handle them

| Risk | Mitigation |
|------|------------|
| Losing hard-won timing behaviour in the port | Port the pacing, grouping and engine logic line by line, and port the prototype's tests with them (pacing, roll-up, alignment, seek-back). |
| YouTube InnerTube changes | Keep the multi-client fallback (ANDROID, IOS, WEB) and keep `yt-dlp` updatable from the app (`tarjuman update`). |
| Edge TTS throttling | One gate with at most 4 in flight and urgent-first priority, retries with backoff, and a Piper fallback that is never cached under the Edge key. |
| Chrome Web Store review | `<all_urls>` moves to optional host permissions, every permission gets a written justification, no remote code is loaded, and a privacy policy ships. |
| Long CPU jobs blocking the API | Whisper runs in a worker thread. Separation and mixing run as subprocesses that can be killed on cancel. |
