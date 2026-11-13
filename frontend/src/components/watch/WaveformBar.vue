<script setup lang="ts">
/* The whole recording as a waveform: what was played (or transcribed) is saffron, the rest is quiet.
   Click or drag to seek; the sentences sit in a thin lane underneath, the current one lit. */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { formatTime } from "@/lib/time";

const props = withDefaults(
  defineProps<{
    peaks: number[];
    /** 0..1: played, or transcribed while Whisper works. */
    progress: number;
    duration: number;
    regions?: { start: number; end: number }[];
    active?: number;
    interactive?: boolean;
    /** Whisper is reading the audio: the edge of the progress glows and moves. */
    scanning?: boolean;
    label?: string;
  }>(),
  { regions: () => [], active: -1, interactive: false, scanning: false, label: "" },
);
const emit = defineEmits<{ seek: [seconds: number] }>();

const box = ref<HTMLElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const hover = ref<number | null>(null); // 0..1
const dragging = ref(false);
let width = 0;
let height = 0;
let ro: ResizeObserver | null = null;
let raf = 0;
let grownAt = 0; // when the bars started growing in
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

const BAR = 3;
const GAP = 2;
const LANE = 6; // the sentences lane

function colors() {
  const s = getComputedStyle(document.documentElement);
  return {
    hi: s.getPropertyValue("--saffron-300").trim() || "#ffd27a",
    deep: s.getPropertyValue("--saffron-500").trim() || "#f0922b",
  };
}

function bars(n: number): number[] {
  const p = props.peaks;
  if (!p.length) return Array.from({ length: n }, () => 0.04);
  const out = new Array<number>(n);
  const step = p.length / n;
  for (let i = 0; i < n; i++) {
    let m = 0;
    const a = Math.floor(i * step);
    const b = Math.max(a + 1, Math.floor((i + 1) * step));
    for (let k = a; k < b && k < p.length; k++) m = Math.max(m, p[k]!);
    out[i] = m;
  }
  return out;
}

function draw(now = performance.now()) {
  const c = canvas.value;
  if (!c || !width) return;
  const dpr = window.devicePixelRatio || 1;
  const ctx = c.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const { hi, deep } = colors();
  const laneH = props.regions.length ? LANE + 6 : 0;
  const waveH = height - laneH;
  const mid = waveH / 2;
  const n = Math.max(8, Math.floor((width + GAP) / (BAR + GAP)));
  const values = bars(n);
  const grow = reduce || !grownAt ? 1 : Math.min(1, (now - grownAt) / 700);
  const ease = 1 - Math.pow(1 - grow, 3);
  const playedX = props.progress * width;
  const hoverX = hover.value == null ? -1 : hover.value * width;
  const grad = ctx.createLinearGradient(0, 0, 0, waveH);
  grad.addColorStop(0, hi);
  grad.addColorStop(1, deep);

  for (let i = 0; i < n; i++) {
    const x = i * (BAR + GAP);
    // Bars grow in from the middle outwards, a ripple across the recording.
    const local = Math.max(0, Math.min(1, ease * 1.6 - (Math.abs(i / n - 0.5) * 1.2)));
    const v = Math.pow(values[i]!, 0.75) * (reduce ? 1 : local);
    const h = Math.max(2, v * (waveH - 6));
    if (x + BAR <= playedX) ctx.fillStyle = grad;
    else if (hoverX >= 0 && x <= hoverX) ctx.fillStyle = "rgba(255, 210, 122, 0.45)";
    else ctx.fillStyle = "rgba(226, 232, 255, 0.24)";
    roundRect(ctx, x, mid - h / 2, BAR, h, 1.5);
  }

  if (props.scanning && playedX > 0) {
    // A soft light at the point Whisper has reached.
    const pulse = reduce ? 0.5 : 0.35 + 0.25 * Math.sin(now / 260);
    const g = ctx.createLinearGradient(playedX - 60, 0, playedX + 8, 0);
    g.addColorStop(0, "rgba(255, 210, 122, 0)");
    g.addColorStop(1, `rgba(255, 210, 122, ${pulse})`);
    ctx.fillStyle = g;
    ctx.fillRect(Math.max(0, playedX - 60), 0, 68, waveH);
  }

  if (laneH && props.duration > 0) {
    const y = height - LANE - 1;
    props.regions.forEach((r, i) => {
      const x0 = (r.start / props.duration) * width;
      const x1 = Math.max(x0 + 2, (r.end / props.duration) * width - 1.5);
      ctx.fillStyle = i === props.active ? hi : "rgba(226, 232, 255, 0.16)";
      roundRect(ctx, x0, y, x1 - x0, LANE, 3);
    });
  }

  if (props.interactive && props.duration > 0) {
    ctx.fillStyle = "#fff";
    ctx.fillRect(Math.min(width - 2, Math.max(0, playedX - 1)), 0, 2, waveH);
  }
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, Math.min(r, w / 2, h / 2));
  else ctx.rect(x, y, w, h);
  ctx.fill();
}

function loop() {
  draw();
  const growing = !reduce && grownAt && performance.now() - grownAt < 800;
  raf = growing || props.scanning ? requestAnimationFrame(loop) : 0;
}
function kick() {
  if (!raf) raf = requestAnimationFrame(loop);
}

function resize() {
  const el = box.value;
  const c = canvas.value;
  if (!el || !c) return;
  const r = el.getBoundingClientRect();
  width = r.width;
  height = r.height;
  const dpr = window.devicePixelRatio || 1;
  c.width = Math.round(width * dpr);
  c.height = Math.round(height * dpr);
  draw();
}

/* ---------- seeking ---------- */

function fraction(e: PointerEvent): number {
  const r = box.value!.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
}
function onMove(e: PointerEvent) {
  if (!props.interactive) return;
  hover.value = fraction(e);
  if (dragging.value) emit("seek", hover.value * props.duration);
  draw();
}
function onDown(e: PointerEvent) {
  if (!props.interactive || !props.duration) return;
  dragging.value = true;
  (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
  emit("seek", fraction(e) * props.duration);
}
function onUp() {
  dragging.value = false;
}
function onLeave() {
  if (dragging.value) return;
  hover.value = null;
  draw();
}
function onKey(e: KeyboardEvent) {
  if (!props.interactive || !props.duration) return;
  const step = e.shiftKey ? 15 : 5;
  const at = props.progress * props.duration;
  const to = { ArrowLeft: at - step, ArrowRight: at + step, Home: 0, End: props.duration - 0.5 }[e.key];
  if (to == null) return;
  e.preventDefault();
  e.stopPropagation();
  emit("seek", Math.max(0, Math.min(props.duration, to)));
}

const hoverTime = computed(() => (hover.value == null ? "" : formatTime(hover.value * props.duration)));
const hoverStyle = computed(() => ({ left: `${(hover.value ?? 0) * 100}%` }));

watch(
  () => props.peaks,
  (p, old) => {
    if (p.length && !old?.length) {
      grownAt = performance.now();
      kick();
    } else draw();
  },
);
watch(() => [props.progress, props.active, props.regions] as const, () => draw());
watch(
  () => props.scanning,
  (s) => (s ? kick() : draw()),
);

onMounted(() => {
  ro = new ResizeObserver(resize);
  if (box.value) ro.observe(box.value);
  resize();
  if (props.peaks.length) {
    grownAt = performance.now();
    kick();
  }
  if (props.scanning) kick();
});
onBeforeUnmount(() => {
  ro?.disconnect();
  cancelAnimationFrame(raf);
});
</script>

<template>
  <div
    ref="box"
    class="wave"
    :class="{ interactive, dragging }"
    :role="interactive ? 'slider' : 'img'"
    :tabindex="interactive ? 0 : undefined"
    :aria-label="label"
    :aria-valuemin="interactive ? 0 : undefined"
    :aria-valuemax="interactive ? Math.round(duration) : undefined"
    :aria-valuenow="interactive ? Math.round(progress * duration) : undefined"
    :aria-valuetext="interactive ? formatTime(progress * duration) : undefined"
    @pointermove="onMove"
    @pointerdown="onDown"
    @pointerup="onUp"
    @pointercancel="onUp"
    @pointerleave="onLeave"
    @keydown="onKey"
  >
    <canvas ref="canvas" aria-hidden="true"></canvas>
    <span v-if="interactive && hover != null" class="tip" :style="hoverStyle">{{ hoverTime }}</span>
  </div>
</template>

<style scoped>
.wave {
  position: relative;
  width: 100%;
  height: 100%;
  touch-action: none;
  border-radius: 8px;
}
.wave canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.wave.interactive {
  cursor: pointer;
}
.wave:focus-visible {
  outline: 2px solid var(--saffron-300);
  outline-offset: 4px;
}
.tip {
  position: absolute;
  top: -26px;
  transform: translateX(-50%);
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(5, 7, 26, 0.9);
  color: #fff;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  pointer-events: none;
  white-space: nowrap;
}
</style>
