<script setup lang="ts">
/* The video as a strip of its sentences: where people speak, which lines are already translated
   (saffron) and which are still on their way (grey), and the one being said. Hovering shows the
   sentence at that moment; click or drag to go there. Time runs left to right, as on every player. */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { usePrefs } from "@/composables/prefs";
import { chapters, cues, getPlayer, seekTo, session, tr } from "@/composables/session";
import { chapterAt } from "@/lib/chapters";
import { activeIndex } from "@/lib/cues";
import { formatTime } from "@/lib/time";

const { t } = useI18n();
const prefs = usePrefs();
const marks = computed(() => (prefs.chapters ? chapters.value : []));
const box = ref<HTMLElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const hover = ref<number | null>(null); // seconds under the pointer
const dragging = ref(false);
let width = 0;
let height = 0;
let ro: ResizeObserver | null = null;
let raf = 0;

const duration = computed(() => {
  const fromPlayer = (() => {
    try {
      return getPlayer()?.getDuration() || 0;
    } catch {
      return 0;
    }
  })();
  const last = cues.value.length ? cues.value[cues.value.length - 1]!.end : 0;
  return Math.max(session.lengthSeconds || 0, fromPlayer, last, 1);
});
const translated = computed(() => tr.value.reduce((n, s) => n + (s ? 1 : 0), 0));
const pct = computed(() => (cues.value.length ? Math.round((translated.value / cues.value.length) * 100) : 0));

function colors() {
  const s = getComputedStyle(document.documentElement);
  const v = (name: string, fallback: string) => s.getPropertyValue(name).trim() || fallback;
  return {
    accent: v("--accent", "#ffd27a"),
    strong: v("--accent-strong", "#f0922b"),
    line: v("--text-3", "#8a90b8"),
    track: v("--surface-3", "#212a60"),
  };
}

function draw() {
  raf = 0;
  const c = canvas.value;
  if (!c || !width) return;
  const g = c.getContext("2d");
  if (!g) return;
  const dpr = window.devicePixelRatio || 1;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, width, height);
  const col = colors();
  const d = duration.value;
  const x = (sec: number) => (sec / d) * width;
  const mid = height / 2;
  const lane = Math.max(6, height * 0.36);

  // The track.
  g.fillStyle = col.track;
  rr(g, 0, mid - 2, width, 4, 2);

  // Each sentence: translated ones in saffron, the rest grey; the one being said full colour.
  const played = x(session.time);
  cues.value.forEach((cue, i) => {
    const x0 = x(cue.start);
    const w = Math.max(1.5, x(cue.end) - x0 - 1);
    const on = i === session.curIdx;
    const done = !!tr.value[i] || session.already;
    g.globalAlpha = on ? 1 : x0 + w <= played ? 0.95 : 0.55;
    g.fillStyle = on ? col.strong : done ? col.accent : col.line;
    rr(g, x0, mid - lane / 2, w, lane, Math.min(3, w / 2));
  });
  g.globalAlpha = 1;

  // Chapters: the strip is cut where each one starts, as on YouTube's own bar.
  for (const ch of marks.value) {
    if (ch.start <= 0) continue;
    g.clearRect(Math.round(x(ch.start)) - 1.5, 0, 3, height);
  }

  // What has been played: a soft veil up to the playhead.
  g.fillStyle = "rgba(255, 210, 122, 0.10)";
  g.fillRect(0, 0, played, height);

  // Hover line.
  if (hover.value != null) {
    g.fillStyle = col.line;
    g.fillRect(Math.round(x(hover.value)), 2, 1, height - 4);
  }
  // Playhead.
  g.fillStyle = col.strong;
  g.fillRect(Math.round(played) - 1, 0, 2, height);
  g.beginPath();
  g.arc(played, mid, dragging.value ? 6 : 4.5, 0, Math.PI * 2);
  g.fill();
}

function rr(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  g.beginPath();
  if (g.roundRect) g.roundRect(x, y, w, h, r);
  else g.rect(x, y, w, h);
  g.fill();
}
function schedule() {
  if (!raf) raf = requestAnimationFrame(draw);
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

/* ---------- pointer and keys ---------- */

function secAt(e: PointerEvent): number {
  const r = box.value!.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * duration.value;
}
function onMove(e: PointerEvent) {
  hover.value = secAt(e);
  if (dragging.value) seekTo(hover.value, session.playing);
  schedule();
}
function onDown(e: PointerEvent) {
  dragging.value = true;
  (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
  seekTo(secAt(e), session.playing);
  schedule();
}
function onUp() {
  dragging.value = false;
  schedule();
}
function onLeave() {
  if (!dragging.value) hover.value = null;
  schedule();
}
function onKey(e: KeyboardEvent) {
  const step = e.shiftKey ? 30 : 5;
  const to = { ArrowLeft: session.time - step, ArrowRight: session.time + step, Home: 0, End: duration.value - 1 }[e.key];
  if (to == null) return;
  e.preventDefault();
  e.stopPropagation(); // the page's arrow keys move by sentence; here they move by seconds
  seekTo(Math.max(0, Math.min(duration.value, to)), session.playing);
}

/* The sentence under the pointer, for the preview card. */
const preview = computed(() => {
  if (hover.value == null) return null;
  const i = activeIndex(cues.value, hover.value);
  const near = i >= 0 ? i : cues.value.findIndex((c) => c.start > hover.value!);
  const cue = near >= 0 ? cues.value[near] : undefined;
  const text = cue ? tr.value[near] || cue.src : "";
  const k = chapterAt(marks.value, hover.value);
  return {
    chapter: k >= 0 ? marks.value[k]!.title : "",
    time: formatTime(hover.value),
    text: text.length > 110 ? text.slice(0, 108) + "…" : text,
    pending: !!cue && !tr.value[near] && !session.already,
    left: `${Math.max(8, Math.min(92, (hover.value / duration.value) * 100))}%`,
  };
});

const current = computed(() => {
  const k = chapterAt(marks.value, session.time);
  return k >= 0 ? marks.value[k]!.title : "";
});

watch(() => [session.time, session.curIdx, cues.value, tr.value, duration.value, marks.value] as const, schedule, { deep: false });
watch(() => tr.value.length, schedule);

onMounted(() => {
  ro = new ResizeObserver(resize);
  if (box.value) ro.observe(box.value);
  resize();
});
onBeforeUnmount(() => {
  ro?.disconnect();
  cancelAnimationFrame(raf);
});
</script>

<template>
  <div class="tl" dir="ltr">
    <div
      ref="box"
      class="tl__bar"
      :class="{ dragging }"
      role="slider"
      tabindex="0"
      :aria-label="t('watch.timeline.label')"
      :aria-valuemin="0"
      :aria-valuemax="Math.round(duration)"
      :aria-valuenow="Math.round(session.time)"
      :aria-valuetext="formatTime(session.time)"
      @pointermove="onMove"
      @pointerdown="onDown"
      @pointerup="onUp"
      @pointercancel="onUp"
      @pointerleave="onLeave"
      @keydown="onKey"
    >
      <canvas ref="canvas" aria-hidden="true"></canvas>
      <Transition name="peek">
        <div v-if="preview" class="tl__peek" :style="{ left: preview.left }">
          <span v-if="preview.chapter" class="tl__chap" dir="auto">{{ preview.chapter }}</span>
          <span class="tl__time">{{ preview.time }}</span>
          <span v-if="preview.text" class="tl__text" :class="{ pending: preview.pending }" dir="auto">{{ preview.text }}</span>
        </div>
      </Transition>
    </div>
    <div class="tl__legend" :dir="$i18n.locale === 'ar' ? 'rtl' : 'ltr'">
      <span><i class="k done"></i>{{ t("watch.timeline.done", { pct }) }}</span>
      <span v-if="pct < 100 && !session.already"><i class="k todo"></i>{{ t("watch.timeline.todo") }}</span>
      <Transition name="peek" mode="out-in">
        <span v-if="current" :key="current" class="tl__now" dir="auto">{{ t("watch.timeline.chapter", { title: current }) }}</span>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.tl {
  margin-top: var(--s-2);
}
.tl__bar {
  position: relative;
  height: 22px;
  cursor: pointer;
  touch-action: none;
  border-radius: 6px;
  transition: height 180ms var(--ease);
}
.tl__bar:hover,
.tl__bar.dragging,
.tl__bar:focus-visible {
  height: 32px;
}
.tl__bar:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.tl__bar canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.tl__peek {
  position: absolute;
  bottom: calc(100% + 10px);
  transform: translateX(-50%);
  display: grid;
  gap: 2px;
  max-width: min(360px, 80vw);
  padding: 8px 12px;
  border-radius: var(--r-md);
  background: var(--surface-1);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-2);
  pointer-events: none;
  z-index: 5;
}
.tl__time {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-ink);
  font-variant-numeric: tabular-nums;
}
.tl__chap {
  font-size: var(--fs-sm);
  font-weight: 650;
}
.tl__now {
  margin-inline-start: auto;
  color: var(--text-2);
  font-weight: 600;
  max-width: 60%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  display: block !important;
}
.tl__text {
  font-size: var(--fs-sm);
  line-height: 1.6;
}
.tl__text.pending {
  color: var(--text-2);
}
.peek-enter-active,
.peek-leave-active {
  transition: opacity 120ms var(--ease);
}
.peek-enter-from,
.peek-leave-to {
  opacity: 0;
}
.tl__legend {
  display: flex;
  gap: var(--s-4);
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-3);
}
.tl__legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.k {
  width: 10px;
  height: 6px;
  border-radius: 2px;
}
.k.done {
  background: var(--accent);
}
.k.todo {
  background: var(--text-3);
  opacity: 0.6;
}
@media (prefers-reduced-motion: reduce) {
  .tl__bar {
    transition: none;
  }
}
</style>
