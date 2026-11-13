<script setup lang="ts">
/* Record with the microphone right here: the voice is drawn as it comes in, and when you stop, the
   recording is saved on this computer, transcribed and translated by itself. */
import { onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhMicrophone, PhPause, PhPlay, PhStop, PhTrash } from "@phosphor-icons/vue";
import { formatTime } from "@/lib/time";
import { api } from "@/api/client";

const emit = defineEmits<{ done: [file: File]; close: [] }>();
const { t } = useI18n();

const state = ref<"idle" | "asking" | "recording" | "paused">("idle");
const error = ref("");
/** In the desktop app a refused microphone can be given back with one click. */
const canFix = ref(false);
const fixing = ref(false);

async function fixMic() {
  fixing.value = true;
  try {
    await api.fixMicrophone();
  } catch {
    fixing.value = false;
  }
}
const elapsed = ref(0);
const canvas = ref<HTMLCanvasElement | null>(null);

let stream: MediaStream | null = null;
let rec: MediaRecorder | null = null;
let chunks: Blob[] = [];
let ctx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let buf: Float32Array<ArrayBuffer> | null = null;
let raf = 0;
let clock = 0;
let startedAt = 0;
let before = 0; // seconds recorded before the last pause
const history: number[] = []; // loudness, one per frame, newest last
const MAX_SECONDS = 60 * 60;

function pickType(): string {
  for (const m of ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/mp4"]) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported?.(m)) return m;
  }
  return "";
}

async function start() {
  error.value = "";
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    error.value = t("record.unsupported");
    return;
  }
  state.value = "asking";
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
    });
  } catch (e) {
    state.value = "idle";
    const denied = (e as Error).name === "NotAllowedError";
    error.value = denied ? t("record.denied") : t("record.noMic");
    if (denied) {
      try {
        canFix.value = (await api.desktop()).available;
      } catch {
        canFix.value = false;
      }
      if (canFix.value) error.value = t("record.deniedApp");
    }
    return;
  }
  const type = pickType();
  rec = new MediaRecorder(stream, type ? { mimeType: type, audioBitsPerSecond: 64000 } : undefined);
  chunks = [];
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.start(1000);
  ctx = new AudioContext();
  analyser = ctx.createAnalyser();
  analyser.fftSize = 1024;
  ctx.createMediaStreamSource(stream).connect(analyser);
  buf = new Float32Array(analyser.fftSize);
  history.length = 0;
  before = 0;
  startedAt = performance.now();
  state.value = "recording";
  clock = window.setInterval(tick, 250);
  draw();
}

function tick() {
  if (state.value !== "recording") return;
  elapsed.value = before + (performance.now() - startedAt) / 1000;
  if (elapsed.value >= MAX_SECONDS) void stop();
}

function pause() {
  if (!rec || state.value !== "recording") return;
  rec.pause();
  before += (performance.now() - startedAt) / 1000;
  state.value = "paused";
}
function resume() {
  if (!rec || state.value !== "paused") return;
  rec.resume();
  startedAt = performance.now();
  state.value = "recording";
  draw();
}

function finish(): Promise<Blob> {
  return new Promise((resolve) => {
    if (!rec || rec.state === "inactive") return resolve(new Blob(chunks, { type: rec?.mimeType || "audio/webm" }));
    rec.onstop = () => resolve(new Blob(chunks, { type: rec?.mimeType || "audio/webm" }));
    rec.stop();
  });
}

async function stop() {
  if (state.value !== "recording" && state.value !== "paused") return;
  const blob = await finish();
  release();
  if (blob.size < 2000) {
    error.value = t("record.tooShort");
    return;
  }
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const ext = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "m4a" : "webm";
  const name = `${t("record.fileName")} ${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}.${pad(d.getMinutes())}.${ext}`;
  emit("done", new File([blob], name, { type: blob.type }));
}

async function discard() {
  await finish();
  release();
  emit("close");
}

function release() {
  clearInterval(clock);
  cancelAnimationFrame(raf);
  raf = 0;
  stream?.getTracks().forEach((tr) => tr.stop());
  stream = null;
  void ctx?.close().catch(() => {});
  ctx = null;
  analyser = null;
  rec = null;
  state.value = "idle";
  elapsed.value = 0;
}

function draw() {
  const c = canvas.value;
  if (!c || !analyser || !buf) return;
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth;
  const h = c.clientHeight;
  if (c.width !== Math.round(w * dpr)) {
    c.width = Math.round(w * dpr);
    c.height = Math.round(h * dpr);
  }
  const g = c.getContext("2d")!;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  if (state.value === "recording") {
    analyser.getFloatTimeDomainData(buf);
    let sum = 0;
    for (const x of buf) sum += x * x;
    history.push(Math.min(1, Math.sqrt(sum / buf.length) * 4.2));
  }
  const step = 5;
  const n = Math.floor(w / step);
  while (history.length > n) history.shift();
  const s = getComputedStyle(document.documentElement);
  const color = s.getPropertyValue("--accent-strong").trim() || "#f0922b";
  g.fillStyle = color;
  const start = n - history.length;
  for (let i = 0; i < history.length; i++) {
    const v = Math.max(0.03, Math.pow(history[i]!, 0.8));
    const bh = v * (h - 4);
    const x = (start + i) * step;
    g.globalAlpha = 0.35 + 0.65 * (i / Math.max(1, history.length));
    g.beginPath();
    if (g.roundRect) g.roundRect(x, (h - bh) / 2, 3, bh, 1.5);
    else g.rect(x, (h - bh) / 2, 3, bh);
    g.fill();
  }
  g.globalAlpha = 1;
  if (state.value === "recording") raf = requestAnimationFrame(draw);
}

onBeforeUnmount(() => {
  if (rec && rec.state !== "inactive") rec.stop();
  release();
});

defineExpose({ start });
</script>

<template>
  <div class="rec" :class="state">
    <template v-if="state === 'idle' || state === 'asking'">
      <button class="btn btn--primary" type="button" :disabled="state === 'asking'" @click="start">
        <PhMicrophone :size="18" weight="fill" />
        {{ state === "asking" ? t("record.asking") : t("record.start") }}
      </button>
      <p class="hint">{{ t("record.hint") }}</p>
      <button class="btn btn--quiet btn--sm" type="button" @click="emit('close')">{{ t("common.cancel") }}</button>
    </template>
    <template v-else>
      <span class="dot" aria-hidden="true"></span>
      <span class="time" role="timer" aria-live="off">{{ formatTime(elapsed) }}</span>
      <canvas ref="canvas" class="live" dir="ltr" aria-hidden="true"></canvas>
      <div class="acts">
        <button v-if="state === 'recording'" class="icon-btn" type="button" :aria-label="t('record.pause')" :title="t('record.pause')" @click="pause">
          <PhPause :size="18" weight="fill" />
        </button>
        <button v-else class="icon-btn" type="button" :aria-label="t('record.resume')" :title="t('record.resume')" @click="resume">
          <PhPlay :size="18" weight="fill" />
        </button>
        <button class="icon-btn" type="button" :aria-label="t('record.discard')" :title="t('record.discard')" @click="discard">
          <PhTrash :size="18" />
        </button>
        <button class="btn btn--primary btn--sm" type="button" @click="stop">
          <PhStop :size="16" weight="fill" />
          {{ t("record.stop") }}
        </button>
      </div>
    </template>
    <p v-if="error" class="err" role="alert">
      {{ error }}
      <button v-if="canFix" class="btn btn--primary btn--sm fix" type="button" :disabled="fixing" @click="fixMic">
        <PhMicrophone :size="16" />
        {{ fixing ? t("record.fixing") : t("record.fix") }}
      </button>
    </p>
  </div>
</template>

<style scoped>
.rec {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r-lg);
  border: 1px solid var(--line);
  background: var(--surface-1);
}
.rec.recording,
.rec.paused {
  border-color: color-mix(in srgb, var(--accent-strong) 55%, transparent);
}
.hint {
  flex: 1;
  min-width: 200px;
  font-size: var(--fs-sm);
  opacity: 0.85;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #e5484d;
  flex: none;
}
.recording .dot {
  animation: blink 1.2s ease-in-out infinite;
}
.paused .dot {
  background: var(--surface-3);
}
.time {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  min-width: 52px;
}
.live {
  flex: 1;
  min-width: 140px;
  height: 44px;
}
.acts {
  display: flex;
  align-items: center;
  gap: 6px;
}
.icon-btn {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.icon-btn:hover {
  background: var(--surface-2);
}
.icon-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.fix {
  margin-inline-start: var(--s-2);
  vertical-align: middle;
}
.err {
  flex-basis: 100%;
  color: var(--danger, #e5484d);
  font-size: var(--fs-sm);
}
@keyframes blink {
  50% {
    opacity: 0.25;
  }
}
@media (prefers-reduced-motion: reduce) {
  .recording .dot {
    animation: none;
  }
}
</style>
