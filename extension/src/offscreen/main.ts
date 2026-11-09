/**
 * Offscreen document, used only in live mode (sites without captions):
 *  - takes the tab's audio (tabCapture) and plays it back to the speakers,
 *    because Chrome mutes a tab while it is being captured;
 *  - cuts the audio at natural pauses and sends each phrase to /api/live;
 *  - when dubbing, lowers the original audio and plays the spoken translations in order.
 */
import { Chunker, downsampleTo16k, toPcm16B64, b64ToObjectUrl } from "@/shared/audio";
import { mergeSettings, type Settings } from "@/shared/settings";
import { DEFAULT_BASE } from "@/shared/server";

const MAX_INFLIGHT = 2;
/** At most this many spoken phrases waiting; beyond it we are far behind and drop the oldest. */
const MAX_QUEUE = 3;

let server = DEFAULT_BASE;
let settings: Settings = mergeSettings(null);

let ctx: AudioContext | null = null;
let stream: MediaStream | null = null;
let srcNode: MediaStreamAudioSourceNode | null = null;
let playGain: GainNode | null = null;
let procNode: ScriptProcessorNode | null = null;
let chunker: Chunker | null = null;
let running = false;

let inflight = 0;
let seq = 0;
let lastShown = 0;

function send(msg: Record<string, unknown>) {
  chrome.runtime.sendMessage(msg).catch(() => {});
}

/* ---------------- sending phrases ---------------- */

function onAudio(data: Float32Array) {
  if (!chunker || !ctx) return;
  const chunk = chunker.push(data);
  if (!chunk) return; // not yet, or silence
  // The server is behind: skip this phrase rather than let the delay pile up.
  if (inflight >= MAX_INFLIGHT) return;
  post(toPcm16B64(downsampleTo16k(chunk, ctx.sampleRate)));
}

async function post(b64: string) {
  const id = ++seq;
  inflight++;
  send({ type: "live-status", status: "transcribing" });
  try {
    const r = await fetch(`${server}/api/live`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio_b64: b64, tl: settings.lang || "ar", tts: !!settings.dub, voice: settings.voice || "" }),
    });
    const j = await r.json();
    if (!running) return;
    if (j.ok && j.text) {
      // Replies can arrive out of order; never replace a newer subtitle with an older one.
      if (id > lastShown) {
        lastShown = id;
        send({ type: "live-result", text: j.text, ar: j.ar || "" });
      }
      if (settings.dub) {
        if (j.audio_b64) enqueueAudio(j.audio_b64, j.audio_mime);
        else if (j.ar) speakFallback(j.ar);
      }
    } else if (j && j.ok === false) {
      send({ type: "live-status", status: "error", message: j.message || j.code });
    }
  } catch {
    send({ type: "live-status", status: "server-down" });
  } finally {
    inflight--;
    if (running && !inflight) send({ type: "live-status", status: "listening" });
  }
}

/* ---------------- dub playback ---------------- */

const audioQueue: string[] = [];
let playing: HTMLAudioElement | null = null;

function enqueueAudio(b64: string, mime?: string) {
  audioQueue.push(b64ToObjectUrl(b64, mime));
  if (audioQueue.length > MAX_QUEUE) URL.revokeObjectURL(audioQueue.shift()!);
  if (!playing) playNext();
}

function playNext() {
  const url = audioQueue.shift();
  if (!url) {
    playing = null;
    return;
  }
  const a = new Audio(url);
  // With phrases waiting, speak a little faster to catch up.
  a.playbackRate = audioQueue.length ? 1.2 : 1.05;
  playing = a;
  const done = () => {
    URL.revokeObjectURL(url);
    playNext();
  };
  a.onended = done;
  a.onerror = done;
  a.play().catch(done);
}

function stopAudio() {
  while (audioQueue.length) URL.revokeObjectURL(audioQueue.shift()!);
  if (playing) {
    try {
      playing.pause();
    } catch {}
    playing = null;
  }
  try {
    speechSynthesis.cancel();
  } catch {}
}

// The server returned text but no audio (no voice engine reachable): use the browser's voice.
function speakFallback(text: string) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = settings.lang === "ar" ? "ar-SA" : settings.lang;
    const v = speechSynthesis.getVoices().find((x) => (x.lang || "").toLowerCase().startsWith(settings.lang));
    if (v) u.voice = v;
    speechSynthesis.speak(u);
  } catch {}
}

function applyGain() {
  if (playGain && ctx) playGain.gain.setTargetAtTime(settings.dub ? settings.duck : 1, ctx.currentTime, 0.15);
}

/* ---------------- capture ---------------- */

async function startCapture(streamId: string) {
  await stopCapture();
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: streamId } } as any,
    video: false,
  });
  ctx = new AudioContext();
  chunker = new Chunker(ctx.sampleRate || 48000);
  lastShown = seq;

  srcNode = ctx.createMediaStreamSource(stream);

  // 1) The tab's sound back to the speakers (lowered while dubbing).
  playGain = ctx.createGain();
  srcNode.connect(playGain);
  playGain.connect(ctx.destination);
  applyGain();

  // 2) A full-volume copy for transcription. ScriptProcessor is deprecated but
  // needs no separate worklet file, and 4096-sample frames are plenty here.
  procNode = ctx.createScriptProcessor(4096, 1, 1);
  procNode.onaudioprocess = (e) => {
    if (running) onAudio(e.inputBuffer.getChannelData(0));
  };
  const mute = ctx.createGain();
  mute.gain.value = 0;
  srcNode.connect(procNode);
  procNode.connect(mute);
  mute.connect(ctx.destination);

  running = true;
  send({ type: "live-status", status: "listening" });
}

async function stopCapture() {
  running = false;
  stopAudio();
  try {
    procNode?.disconnect();
  } catch {}
  try {
    srcNode?.disconnect();
  } catch {}
  try {
    stream?.getTracks().forEach((t) => t.stop());
  } catch {}
  try {
    await ctx?.close();
  } catch {}
  ctx = null;
  stream = null;
  srcNode = null;
  procNode = null;
  playGain = null;
  chunker = null;
}

/* ---------------- messages ---------------- */

chrome.runtime.onMessage.addListener((msg, _sender, respond) => {
  if (!msg || msg.target !== "offscreen") return;

  if (msg.type === "start-capture") {
    if (msg.server) server = msg.server;
    settings = mergeSettings(settings, msg.settings);
    startCapture(msg.streamId)
      .then(() => respond({ ok: true }))
      .catch((e) => respond({ ok: false, message: String((e && e.message) || e) }));
    return true;
  }

  if (msg.type === "stop-capture") {
    stopCapture().then(() => respond({ ok: true }));
    return true;
  }

  if (msg.type === "update-settings") {
    settings = mergeSettings(settings, msg.settings);
    if (!settings.dub) stopAudio();
    applyGain();
    respond({ ok: true });
  }
});
