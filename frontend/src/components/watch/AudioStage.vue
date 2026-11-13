<script setup lang="ts">
/* A recording has no picture, so the stage becomes one: the sound itself, live, behind the sentence
   being said, and the whole recording as a waveform to move through by sentence or by second. */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  PhArrowClockwise,
  PhArrowCounterClockwise,
  PhPause,
  PhPlay,
  PhRepeatOnce,
  PhSkipBack,
  PhSkipForward,
  PhWaveform,
} from "@phosphor-icons/vue";
import WaveformBar from "./WaveformBar.vue";
import { armLoop, applySpeed, cues, seekTo, session, stepLine, togglePlay } from "@/composables/session";
import { usePrefs } from "@/composables/prefs";
import { formatTime } from "@/lib/time";

const props = defineProps<{
  src: string;
  title: string;
  peaks: number[];
  duration: number;
  /** The Whisper model that made the transcript. */
  model: string;
}>();

const { t, te } = useI18n();
const prefs = usePrefs();
const el = ref<HTMLAudioElement | null>(null);
const viz = ref<HTMLCanvasElement | null>(null);
const length = ref(props.duration || 0);
defineExpose({ media: el });

const progress = computed(() => (length.value > 0 ? Math.min(1, session.time / length.value) : 0));
const regions = computed(() => cues.value.map((c) => ({ start: c.start, end: c.end })));
const speeds = [0.75, 1, 1.25, 1.5];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

function onSeek(sec: number) {
  seekTo(sec, session.playing);
}
function skip(by: number) {
  seekTo(Math.max(0, Math.min(length.value, session.time + by)), session.playing);
}
function nextSpeed() {
  const i = speeds.indexOf(prefs.speed);
  prefs.speed = speeds[(i + 1) % speeds.length]!;
  applySpeed();
}
function toggleLoop() {
  prefs.loop = !prefs.loop;
  if (prefs.loop) armLoop();
}

/* ---------- the live spectrum ---------- */

let ctx: AudioContext | null = null;
let analyser: AnalyserNode | null = null;
let freq: Uint8Array<ArrayBuffer> | null = null;
let raf = 0;
let ro: ResizeObserver | null = null;
const N = 56; // bars, mirrored from the middle
const level = new Float32Array(N);

/** The element keeps playing through the speakers as usual; a copy of its sound is only measured
 *  (captureStream), so nothing here can silence it. Without it the bars follow the waveform. */
function listen() {
  if (analyser || reduce) return;
  const v = el.value as (HTMLAudioElement & { captureStream?: () => MediaStream }) | null;
  if (!v?.captureStream) return;
  try {
    const stream = v.captureStream();
    if (!stream.getAudioTracks().length) return;
    ctx = new AudioContext();
    const source = ctx.createMediaStreamSource(stream);
    analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.78;
    const silent = ctx.createGain();
    silent.gain.value = 0;
    source.connect(analyser);
    analyser.connect(silent);
    silent.connect(ctx.destination);
    freq = new Uint8Array(analyser.frequencyBinCount);
    void ctx.resume().catch(() => {});
  } catch {
    analyser = null;
  }
}

function targets(): Float32Array {
  const out = new Float32Array(N);
  if (!session.playing) return out;
  if (analyser && freq) {
    analyser.getByteFrequencyData(freq);
    // Speech lives low: spread the bars over ~80 Hz-6 kHz on a log scale.
    const nyq = (ctx?.sampleRate || 48000) / 2;
    for (let i = 0; i < N; i++) {
      const f0 = 80 * Math.pow(6000 / 80, i / N);
      const f1 = 80 * Math.pow(6000 / 80, (i + 1) / N);
      const a = Math.floor((f0 / nyq) * freq.length);
      const b = Math.max(a + 1, Math.floor((f1 / nyq) * freq.length));
      let m = 0;
      for (let k = a; k < b && k < freq.length; k++) m = Math.max(m, freq[k]!);
      out[i] = Math.pow(m / 255, 1.4);
    }
    return out;
  }
  // No analyser: the loudness of the recording around this moment, shaped like a voice.
  const p = props.peaks;
  if (p.length && length.value) {
    const at = Math.floor((session.time / length.value) * p.length);
    const v = p[Math.min(p.length - 1, at)] ?? 0;
    for (let i = 0; i < N; i++) {
      const shape = Math.exp(-Math.pow((i - N * 0.28) / (N * 0.3), 2));
      out[i] = v * shape * (0.75 + 0.25 * Math.sin(performance.now() / 90 + i));
    }
  }
  return out;
}

function frame() {
  const c = viz.value;
  if (!c) return;
  const g = c.getContext("2d");
  if (!g) return;
  const dpr = window.devicePixelRatio || 1;
  const w = c.width / dpr;
  const h = c.height / dpr;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  const tg = targets();
  let moving = false;
  for (let i = 0; i < N; i++) {
    // Rise fast, fall slowly: it reads as speech, not flicker.
    level[i] = tg[i]! > level[i]! ? level[i]! + (tg[i]! - level[i]!) * 0.5 : level[i]! * 0.9;
    if (level[i]! > 0.004) moving = true;
  }
  const slot = w / 2 / N;
  const bw = Math.max(2, slot * 0.55);
  const mid = h / 2;
  const grad = g.createLinearGradient(0, mid - h * 0.45, 0, mid + h * 0.45);
  grad.addColorStop(0, "rgba(255, 210, 122, 0.0)");
  grad.addColorStop(0.35, "rgba(255, 210, 122, 0.55)");
  grad.addColorStop(0.5, "rgba(240, 146, 43, 0.75)");
  grad.addColorStop(0.65, "rgba(255, 210, 122, 0.55)");
  grad.addColorStop(1, "rgba(255, 210, 122, 0.0)");
  g.fillStyle = grad;
  for (let i = 0; i < N; i++) {
    const bh = Math.max(2, level[i]! * h * 0.9);
    for (const side of [-1, 1]) {
      const x = w / 2 + side * (i * slot + slot / 2) - bw / 2;
      g.beginPath();
      if (g.roundRect) g.roundRect(x, mid - bh / 2, bw, bh, bw / 2);
      else g.rect(x, mid - bh / 2, bw, bh);
      g.fill();
    }
  }
  raf = session.playing || moving ? requestAnimationFrame(frame) : 0;
}
function animate() {
  if (!raf && !reduce) raf = requestAnimationFrame(frame);
}
function sizeViz() {
  const c = viz.value;
  if (!c) return;
  const r = c.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  c.width = Math.round(r.width * dpr);
  c.height = Math.round(r.height * dpr);
  if (!raf) frame();
}

watch(
  () => session.playing,
  (on) => {
    if (on) {
      listen();
      void ctx?.resume().catch(() => {});
    }
    animate();
  },
);
watch(
  () => props.duration,
  (d) => {
    if (d && !length.value) length.value = d;
  },
);

function onMeta() {
  const d = el.value?.duration;
  if (d && Number.isFinite(d)) length.value = d;
}

onMounted(() => {
  ro = new ResizeObserver(sizeViz);
  if (viz.value) ro.observe(viz.value);
});
onBeforeUnmount(() => {
  ro?.disconnect();
  cancelAnimationFrame(raf);
  void ctx?.close().catch(() => {});
});

const lang = computed(() => {
  const c = session.srcLang;
  if (!c || c === "auto") return "";
  return te("langs." + c) ? t("langs." + c) : c;
});
</script>

<template>
  <div class="audio" :class="{ playing: session.playing }">
    <audio ref="el" :src="src" preload="auto" @loadedmetadata="onMeta" @durationchange="onMeta"></audio>

    <header class="head" :dir="prefs.uiLang === 'ar' ? 'rtl' : 'ltr'">
      <span class="badge"><PhWaveform :size="16" weight="bold" />{{ t("watch.audio.badge") }}</span>
      <strong class="title" :title="title">{{ title }}</strong>
      <span class="facts">
        <span v-if="length">{{ formatTime(length) }}</span>
        <span v-if="lang">{{ lang }}</span>
        <span v-if="model" :title="t('watch.audio.modelHint')">Whisper {{ model }}</span>
      </span>
    </header>

    <div class="center">
      <canvas ref="viz" class="viz" aria-hidden="true"></canvas>
      <div class="words"><slot /></div>
    </div>

    <div class="deck">
      <div class="track">
        <WaveformBar
          :peaks="peaks"
          :progress="progress"
          :duration="length"
          :regions="regions"
          :active="session.curIdx"
          interactive
          :label="t('watch.audio.seek')"
          @seek="onSeek"
        />
      </div>
      <div class="controls">
        <span class="time">{{ formatTime(session.time) }}<i>/</i>{{ formatTime(length) }}</span>
        <div class="buttons">
          <button type="button" class="ctl" :aria-label="t('watch.audio.back5')" :title="t('watch.audio.back5')" @click="skip(-5)">
            <PhArrowCounterClockwise :size="20" /><small>5</small>
          </button>
          <button type="button" class="ctl" :aria-label="t('watch.audio.prevLine')" :title="t('watch.audio.prevLine')" @click="stepLine(-1)">
            <PhSkipBack :size="20" weight="fill" />
          </button>
          <button type="button" class="play" :aria-label="session.playing ? t('watch.audio.pause') : t('watch.audio.play')" @click="togglePlay">
            <PhPause v-if="session.playing" :size="26" weight="fill" />
            <PhPlay v-else :size="26" weight="fill" />
          </button>
          <button type="button" class="ctl" :aria-label="t('watch.audio.nextLine')" :title="t('watch.audio.nextLine')" @click="stepLine(1)">
            <PhSkipForward :size="20" weight="fill" />
          </button>
          <button type="button" class="ctl" :aria-label="t('watch.audio.fwd5')" :title="t('watch.audio.fwd5')" @click="skip(5)">
            <PhArrowClockwise :size="20" /><small>5</small>
          </button>
        </div>
        <div class="extra">
          <button type="button" class="chip" :aria-label="t('watch.audio.speed')" :title="t('watch.audio.speed')" @click="nextSpeed">
            {{ prefs.speed }}×
          </button>
          <button
            type="button"
            class="chip"
            :class="{ on: prefs.loop }"
            :aria-pressed="prefs.loop"
            :aria-label="t('watch.audio.loop')"
            :title="t('watch.audio.loop')"
            @click="toggleLoop"
          >
            <PhRepeatOnce :size="18" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.audio {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  grid-template-rows: auto 1fr auto;
  background:
    radial-gradient(60% 55% at 50% 48%, rgba(53, 80, 214, 0.35), transparent 70%),
    radial-gradient(90% 70% at 85% 0%, rgba(255, 210, 122, 0.07), transparent 60%),
    linear-gradient(170deg, var(--lapis-700), var(--lapis-900) 75%);
  color: #eef0fb;
}
.head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px 0;
  min-width: 0;
  font-size: 13px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--r-pill);
  background: rgba(255, 210, 122, 0.12);
  color: var(--saffron-300);
  font-weight: 600;
  flex: none;
}
.title {
  font-weight: 600;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.facts {
  display: flex;
  gap: 10px;
  margin-inline-start: auto;
  color: #9aa2cf;
  flex: none;
  font-variant-numeric: tabular-nums;
}
.center {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 0;
}
.viz {
  position: absolute;
  inset: 8% 4%;
  width: 92%;
  height: 84%;
  opacity: 0.55;
}
.words {
  position: relative;
  z-index: 1;
  width: 100%;
  padding: 0 6%;
}
.words :deep(.subs) {
  inset-inline: auto;
}
.deck {
  padding: 0 18px 14px;
  display: grid;
  gap: 8px;
}
.track {
  height: clamp(44px, 9vh, 76px);
}
.controls {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
}
.time {
  font-size: 13px;
  color: #c3c8e6;
  font-variant-numeric: tabular-nums;
}
.time i {
  font-style: normal;
  opacity: 0.45;
  margin: 0 4px;
}
.buttons {
  display: flex;
  align-items: center;
  gap: 6px;
}
.extra {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.ctl,
.chip,
.play {
  display: inline-grid;
  place-items: center;
  border: 0;
  color: #eef0fb;
  background: transparent;
  cursor: pointer;
  transition: background 150ms var(--ease), transform 150ms var(--ease);
}
.ctl {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 50%;
}
.ctl small {
  position: absolute;
  font-size: 8px;
  font-weight: 700;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -45%);
}
.ctl:hover,
.chip:hover {
  background: rgba(255, 255, 255, 0.1);
}
.play {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: var(--saffron-300);
  color: var(--lapis-900);
  box-shadow: 0 6px 22px rgba(255, 210, 122, 0.28);
}
.play:hover {
  transform: scale(1.05);
}
.play:active {
  transform: scale(0.96);
}
.chip {
  min-width: 40px;
  height: 32px;
  padding: 0 10px;
  border-radius: var(--r-pill);
  border: 1px solid rgba(255, 255, 255, 0.16);
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.chip.on {
  background: rgba(255, 210, 122, 0.16);
  border-color: rgba(255, 210, 122, 0.6);
  color: var(--saffron-300);
}
.ctl:focus-visible,
.chip:focus-visible,
.play:focus-visible {
  outline: 2px solid var(--saffron-300);
  outline-offset: 2px;
}
@media (max-width: 759px) {
  .head {
    padding: 10px 12px 0;
  }
  .facts {
    display: none;
  }
  .deck {
    padding: 0 12px 10px;
  }
  .controls {
    grid-template-columns: auto 1fr;
  }
  .time {
    grid-row: 1;
  }
  .buttons {
    grid-column: 1 / -1;
    justify-content: center;
  }
  .extra {
    grid-row: 1;
    grid-column: 2;
  }
  .ctl {
    width: 36px;
    height: 36px;
  }
  .play {
    width: 48px;
    height: 48px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .play,
  .ctl,
  .chip {
    transition: none;
  }
}
</style>
