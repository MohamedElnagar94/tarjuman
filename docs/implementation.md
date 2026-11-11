# Tarjuman — implementation notes

These notes explain how the system works and why it is built the way it is. The contract between the parts (routes, shapes, security rules) is in [specs.md](specs.md). The phases and reasoning behind the rewrite are in [plan.md](plan.md).

## The parts

```
 Browser tab (web app, Vue)          Browser extension (MV3)
 ├─ player + subtitle overlay         ├─ content script on YouTube / any site
 └─ shared dub engine ◄────────┐      ├─ offscreen document (tab audio)
                               │      └─ shared dub engine (bundled)
                               ▼
               Local server — python -m tarjuman (FastAPI, 127.0.0.1:4318)
 ├─ captions    YouTube InnerTube → parse → repair → align
 ├─ translate   Google gtx (batched) → MyMemory, disk cache, user edits
 ├─ voice       priority gate → Edge neural voices / Piper / Google, disk cache
 ├─ dub         sentences → pacing → measured plans
 ├─ ai          Claude (official SDK) or OpenAI-compatible: dub script, summary, Q&A
 ├─ asr         faster-whisper in a worker thread
 └─ jobs        yt-dlp, mixer, separator and ffmpeg as subprocesses that can be killed
```

Everything runs on the user's computer. The server reaches out only to YouTube, the translation services, Microsoft's voice service and, if the user turns it on, an AI provider.

## Getting captions right

YouTube captions are messy in three different ways, and each one gets its own repair step in `captions/repair.py`:

| Problem | Where it shows up | Repair |
|---|---|---|
| Rolling windows ("so we" → "so we went home") | some ASR tracks | `dedupe_rolling` keeps the longest |
| Roll-up captions: each line stays up while the next appears and repeats its end | many channels (freeCodeCamp, for example) | `unroll_lines` keeps only the new words, after detecting overlap in at least 30% of lines |
| ASR chopped mid-sentence with no punctuation | auto-generated tracks | `reconstruct_asr` regroups lines by time gaps and splits at sentence punctuation; very long runs are re-cut at commas |

When YouTube already has an Arabic track, the English track is still fetched to show bilingual subtitles. The two tracks split speech in different places, so `align_source` gives each English line to exactly one Arabic line: the one it overlaps most. Without this, the middle line would appear under two neighbours and look repeated.

## Translation

`Translator.translate_many` translates many lines at once:

1. User edits win, then the cache.
2. The rest go out in chunks (up to 24 lines or 1,400 characters), joined by newlines, one Google gtx request per chunk. If the line count comes back different, that chunk is retried line by line.
3. A 429 response puts Google on a five-minute cooldown, and MyMemory takes over meanwhile. MyMemory accepts 500 bytes a query, so a longer text is sent in pieces cut at sentence or word ends and joined back.
4. Lines that failed are left out of the result, so callers retry them later instead of caching an empty string.

## Voices

`TtsService.speak` returns audio bytes and a duration, and every clip is cached on disk by a key built from (voice, rate, text). The cache key layout is the same as the prototype's, so an existing cache carries over.

- **The priority gate** (`voice/gate.py`) allows eight requests in flight. Measured on a slow connection, eight give the most throughput; beyond that requests only queue up on Microsoft's side. Priority 3 is the spot the user just seeked to, 2 is "play now", 1 is "prepare what's next" and 0 is background warm-up. A request for a sentence already waiting at lower priority raises that sentence's priority (`bump`).
- **In-flight dedupe.** If two callers ask for the same sentence, it is synthesized once.
- **Fallbacks are never cached under the requested key.** When Edge fails and Piper speaks instead, that clip is returned but not stored as the Edge clip. Storing it would keep the wrong voice and the wrong duration for that sentence forever.
- **Learned speed.** Each voice's real speaking speed (characters per second at rate 0) is learned from the clips it produces, with an exponential moving average. Estimates get better the more a voice is used.
- **Pronunciation.** The user's dictionary is applied to the spoken text only, never to the written subtitles.

## Live dubbing

### Server side: plans (`dub/live.py`)

1. **Sentences.** `group_dub_blocks` merges caption lines into sentences. Spoken filler ("um", "you know", "basically") and wordy phrasings ("in order to" → "to") are removed before translating, which makes the Arabic shorter.
2. **Text.** Each sentence gets its spoken text from one of three sources: the AI script writer (when enabled; it writes natural lines sized to the sentence's time), YouTube's own Arabic track, or the translator. Sentences containing a line the user corrected are rebuilt from the line translations, so the correction is what gets spoken.
3. **Pacing** (`pace_blocks`). For each sentence, look ahead at a window of about 12 s inside its paragraph and choose the speed that finishes the window on time, starting from where the dub actually is. As a result:
   - a roomy sentence lends its time to a crowded neighbour;
   - after the dub falls behind, the next sentences speed up a little until it catches up;
   - the speed changes gradually between neighbours (at most +10% or −8% per step);
   - the dub never trails the speaker by more than 0.8 s at a sentence boundary.
4. **Measurement.** Before answering, every sentence is synthesized once at its first-pass rate and measured. Pacing then runs again with the real durations. If the final rate is within ×0.85–1.2 of the cached clip, the plan says "play the cached clip at `playRate`"; otherwise the new clip is generated in the background.

### Client side: the engine (`shared/dub-engine`)

The engine runs a 100 ms tick against a small media adapter (the YouTube player, an HTML5 video, or a site's `<video>`):

- **It never cuts or skips a late sentence.** It plays it faster instead: up to 1.3× extra, capped at 1.65× effective speed.
- **It holds the video only when it has to:** when the dub is more than 1.8 s behind, or when audio is still missing 1.5 s after a sentence was due. A hold never lasts longer than 15 s.
- **It distrusts the player for one second after it plays or pauses the video.** Players report state changes late, and without this grace period the engine would mistake its own pause for the user's.
- **Seeking into an unprepared range starts over.** The engine bumps a generation counter so late answers for the old position can't claim coverage, holds the video if it was playing before the seek, and requests a small urgent window. In the prototype this was the bug where the dub went silent after seeking back until playback reached the old position.

The simulation tests in `shared/dub-engine/test/` replay these situations with a fake clock: a fast speaker, YouTube's state lag, seeking back.

## Dubbed MP4 (`jobs/runners.py → run_dub`)

1. Download the video, or use the local file.
2. If "remove the speaker's voice" is on, start MDX-Net separation (`media/separator.py`, numpy STFT plus onnxruntime) in a subprocess. It runs on the CPU while synthesis waits on the network.
3. Get captions, or run Whisper if the video has none. Build the sentences.
4. With voice "auto", measure the speaker's pitch per sentence (`media/pitch.py`). When a second speaker is clear (at least 10% of sentences), each sentence gets its speaker's voice; the pitch is smoothed over three sentences.
5. Synthesize every sentence at rate 0 to learn its real length. Pace whole paragraphs from the real lengths, then re-synthesize only the sentences whose speed changed.
6. Schedule: each sentence starts on time, or when the previous one ends. A sentence that would still overflow is made again at `fit_rate`.
7. Mix (`media/mixer.py`): place the clips so they never overlap, put the original audio (or the clean background) underneath with sidechain ducking, and mux. Subtitles can be embedded as a track, or burned in with libass, which shapes Arabic correctly.

Every heavy step is a subprocess registered on the job, so **Cancel** kills it. Whisper runs in-process and checks `job.cancelled` between segments.

Heavy jobs take turns: one Whisper, one dub, one subtitled video and one playlist batch at a time, plus two downloads. A job waiting its turn is `queued`, and it can be cancelled before it starts. A playlist batch takes the same turn for each video it dubs or subtitles.

The separator streams: it decodes a few seconds, separates them, appends them to the output WAV and moves on. Memory use stays at a few megabytes whatever the video's length, and the output is identical to separating the whole track at once (`tests/test_separator.py`).

## Security

The server binds to `0.0.0.0` so a phone on the same Wi-Fi can use the app, which means it has to treat requests carefully. The checks are in `api/security.py` and listed in specs §3. Two of them matter most:

- **Origin and Host checks** stop any website from driving the API through the browser, including through DNS rebinding.
- **`/api/settings` answers only loopback clients**, so a device on the LAN can never read or change the AI key.
- **Other devices must be paired.** The server listens on the Wi-Fi so a phone can use it. Any device other than the computer itself gets nothing until it has opened the pairing link (the QR in Settings → Phone) once. Each paired phone has its own key, so Settings → Phone lists them and any one can be unpaired without touching the others.
- **Only approved extensions.** Any installed extension could call 127.0.0.1. The first one to connect is trusted, and the rest wait for approval in Settings → Extensions.

## Tests

| Suite | Run | Covers |
|---|---|---|
| Backend | `cd backend && ../.venv/bin/python -m pytest` | caption repair, formats, security, pacing, grouping, speakers, API (offline fakes) |
| Dub engine | `npm test` (repo root) | the engine with a fake clock and fake audio |
| Web app | `npm --prefix frontend test` | helpers and player adapters |
| Extension | `npm --prefix extension test` | helpers |

The end-to-end checks were run against real YouTube videos and the real Edge voices: captions, a cold dub plan, speech, a dubbed MP4 with speaker removal and burned subtitles, and an upload transcribed with Whisper.
