<script setup lang="ts">
/* The transcript beside the video. Each line can be read in both languages, clicked to jump there,
   looped, copied or corrected. The line being said fills as it is spoken and its words light up in
   turn; speaker changes and sound tags read as marks, not raw symbols. How it looks is the user's
   (the sliders button, or Settings -> Watching). */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  PhArrowDown,
  PhChatCenteredDots,
  PhCheck,
  PhCopy,
  PhHandsClapping,
  PhMagnifyingGlass,
  PhMusicNotes,
  PhPencilSimple,
  PhRepeatOnce,
  PhSlidersHorizontal,
  PhSmiley,
  PhX,
} from "@phosphor-icons/vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { openLookup } from "@/composables/lookup";
import { T_SIZE, usePrefs } from "@/composables/prefs";
import { chapters, cues, editLine, edited, seekTo, seekToCue, session, tr } from "@/composables/session";
import { chapterAt, chapterHeads, type Chapter } from "@/lib/chapters";
import { toast } from "@/composables/toast";
import { litWords, pieces, speakers, startsTurn, type Piece, type SoundKind } from "@/lib/cueText";
import { formatTime } from "@/lib/time";
import { highlight, tokenize } from "@/lib/words";

const { t } = useI18n();
const prefs = usePrefs();
const q = ref("");
const box = ref<HTMLElement | null>(null);
const search = ref<HTMLInputElement | null>(null);
const editing = ref(-1);
const draft = ref("");
const editor = ref<HTMLTextAreaElement[] | null>(null);
const menu = ref(false);
const menuEl = ref<HTMLElement | null>(null);

const needle = computed(() => q.value.trim().toLowerCase());
const matches = computed(() => {
  if (!needle.value) return null;
  const set = new Set<number>();
  cues.value.forEach((c, i) => {
    if (c.src.toLowerCase().includes(needle.value) || (tr.value[i] || "").toLowerCase().includes(needle.value)) set.add(i);
  });
  return set;
});
const canEdit = computed(() => !session.already);
const RTL = new Set(["ar", "fa", "ur", "he", "ps", "yi"]);
const trDir = computed(() => (RTL.has(session.tl) ? "rtl" : "ltr"));
// The original's direction follows its own language (an Arabic recording reads right to left).
const srcDir = computed(() => (RTL.has(session.srcLang) ? "rtl" : session.srcLang === "auto" ? "auto" : "ltr"));
const showSrc = computed(() => prefs.tView !== "tr" || session.sameLang);
const showTr = computed(() => prefs.tView !== "src" && !session.sameLang);

/* ---------- what each line holds ---------- */

type SrcPart = { kind: "words"; tokens: ReturnType<typeof tokenize> } | Extract<Piece, { kind: "tag" }>;

/** A line as text and sound tags; without the speaker mark when turns are shown. */
function split(text: string): Piece[] {
  if (prefs.tTags) {
    const parts = pieces(text);
    return prefs.tTurns || !startsTurn(text) ? parts : [{ kind: "text", text: text.match(/^\s*\S+\s*/)?.[0] ?? "" }, ...parts];
  }
  const body = prefs.tTurns ? text.replace(/^\s*(?:>>+\s*|[-–—]\s+)/, "") : text;
  return [{ kind: "text", text: body }];
}
/* Computed once per cue list (and when the display options change); the source never changes. */
const srcParts = computed<SrcPart[][]>(() =>
  cues.value.map((c) => split(c.src).map((p) => (p.kind === "text" ? { kind: "words", tokens: tokenize(p.text) } : p))),
);
const trParts = (i: number): Piece[] => (tr.value[i] ? split(tr.value[i]!) : []);
// Speakers are marked only when the captions say when they change.
const hasTurns = computed(() => cues.value.some((c) => startsTurn(c.src)));
const who = computed(() => (prefs.tTurns && hasTurns.value ? speakers(cues.value.map((c) => c.src)) : null));
const turns = computed(() => (prefs.tTurns ? cues.value.map((c, i) => i > 0 && startsTurn(c.src)) : null));

const SOUND_ICON: Record<SoundKind, unknown> = {
  music: PhMusicNotes,
  applause: PhHandsClapping,
  laughter: PhSmiley,
  other: PhChatCenteredDots,
};

/* ---------- chapters: a heading above the first line of each ---------- */

const heads = computed(() => (prefs.chapters && !needle.value && chapters.value.length ? chapterHeads(chapters.value, cues.value) : null));
const curChapter = computed(() => chapterAt(chapters.value, session.time));
function headAt(i: number): { k: number; ch: Chapter } | null {
  const k = heads.value?.get(i);
  return k == null ? null : { k, ch: chapters.value[k]! };
}

/* ---------- the line being said: progress and lit words ---------- */

const frac = computed(() => {
  const c = session.curIdx >= 0 ? cues.value[session.curIdx] : undefined;
  if (!c) return 0;
  return Math.max(0, Math.min(1, (session.time - c.start) / Math.max(0.3, c.end - c.start)));
});
/** The active translation as words, each lit once its share of the line has been spoken. */
const activeWords = computed(() => {
  const i = session.curIdx;
  if (!prefs.karaoke || i < 0 || !tr.value[i]) return null;
  const parts = trParts(i);
  const text = parts.map((p) => (p.kind === "text" ? p.text : "")).join(" ");
  let left = litWords(text, frac.value);
  return parts.map((p) => {
    if (p.kind === "tag") return p;
    const words = p.text.split(/(\s+)/).map((w) => {
      const lit = /\S/.test(w) && left > 0;
      if (lit) left--;
      return { w, lit };
    });
    return { kind: "words" as const, words };
  });
});

/* ---------- following the video, and the way back to it ---------- */

const away = ref(false); // the user scrolled the line being said out of view
let ours = false; // the scroll in progress is ours, not the user's
let oursTimer: number | undefined;

function lineEl(i: number) {
  return box.value?.querySelector<HTMLElement>(`[data-i="${i}"]`) ?? null;
}
function scrollToLine(i: number, smooth = true) {
  const el = lineEl(i);
  const b = box.value;
  if (!el || !b) return;
  const top = el.offsetTop - b.clientHeight / 3;
  if (Math.abs(b.scrollTop - top) < 40) return;
  ours = true;
  clearTimeout(oursTimer);
  oursTimer = window.setTimeout(() => (ours = false), 800);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  b.scrollTo({ top, behavior: smooth && !reduce ? "smooth" : "auto" });
}
function onScroll() {
  if (ours || session.curIdx < 0) return;
  const el = lineEl(session.curIdx);
  const b = box.value;
  if (!el || !b) return;
  const r = el.getBoundingClientRect();
  const v = b.getBoundingClientRect();
  away.value = r.bottom < v.top || r.top > v.bottom;
}
function backToNow() {
  away.value = false;
  scrollToLine(session.curIdx);
}

/* Keep the line being spoken in view, a third of the way down, unless the user is searching,
   editing, or reading elsewhere. */
watch(
  () => session.curIdx,
  async (i) => {
    if (i < 0 || !prefs.follow || needle.value || editing.value >= 0 || away.value) return;
    await nextTick();
    scrollToLine(i);
  },
);

/* ---------- clicks and actions ---------- */

function onClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  const row = target.closest<HTMLElement>("[data-i]");
  if (!row || target.closest(".edit-box, .acts")) return;
  const i = Number(row.dataset.i);
  const w = target.closest<HTMLElement>(".w");
  if (w) return void openLookup(w.dataset.w || w.textContent || "", i, w);
  away.value = false;
  seekToCue(i);
}

function loopLine(i: number) {
  seekToCue(i);
  prefs.loop = true;
  toast(t("transcript.looping"));
}
async function copyLine(i: number) {
  const c = cues.value[i];
  if (!c) return;
  try {
    await navigator.clipboard.writeText([c.src, tr.value[i]].filter(Boolean).join("\n"));
    toast(t("transcript.copied"), { tone: "ok" });
  } catch {
    toast(t("export.subs.copyBlocked"), { tone: "danger" });
  }
}

async function startEdit(i: number) {
  editing.value = i;
  draft.value = tr.value[i] || "";
  await nextTick();
  const el = editor.value?.[0];
  el?.focus();
  el?.select();
}
function cancelEdit() {
  editing.value = -1;
}
async function saveEdit() {
  const i = editing.value;
  editing.value = -1;
  if (i >= 0) await editLine(i, draft.value);
}
function onEditKey(e: KeyboardEvent) {
  e.stopPropagation();
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    void saveEdit();
  } else if (e.key === "Escape") {
    e.preventDefault();
    cancelEdit();
  }
}

/* ---------- the display menu ---------- */

const viewOptions = computed(() => [
  { value: "both" as const, label: t("transcript.view.both") },
  { value: "tr" as const, label: t("transcript.view.tr") },
  { value: "src" as const, label: t("transcript.view.src") },
]);
const densityOptions = computed(() => [
  { value: "cozy" as const, label: t("transcript.density.cozy") },
  { value: "compact" as const, label: t("transcript.density.compact") },
]);
function onDocClick(e: MouseEvent) {
  if (menu.value && menuEl.value && !menuEl.value.contains(e.target as Node)) menu.value = false;
}
onMounted(() => document.addEventListener("click", onDocClick, true));
onBeforeUnmount(() => {
  document.removeEventListener("click", onDocClick, true);
  clearTimeout(oursTimer);
});

const style = computed(() => ({ "--t-size": prefs.tSize + "px" }));

defineExpose({ focusSearch: () => search.value?.focus() });
</script>

<template>
  <section class="tp" :class="[prefs.tDensity, { notimes: !prefs.tTimes }]" :style="style" :aria-label="t('transcript.title')">
    <header class="tp__head">
      <h2 class="tp__title">{{ t("transcript.title") }}</h2>
      <div class="tp__search">
        <PhMagnifyingGlass :size="16" aria-hidden="true" />
        <label class="sr-only" for="tq">{{ t("transcript.search") }}</label>
        <input id="tq" ref="search" v-model="q" type="search" :placeholder="t('transcript.searchPlaceholder')" autocomplete="off" @keydown.esc="q = ''" />
        <output v-if="matches" class="count" for="tq">{{ t("transcript.matches", { n: matches.size }) }}</output>
      </div>
      <label class="follow">
        <span>{{ t("transcript.follow") }}</span>
        <ToggleSwitch v-model="prefs.follow" :label="t('transcript.followHint')" />
      </label>
      <div ref="menuEl" class="menu-wrap">
        <button
          type="button"
          class="btn btn--quiet btn--icon btn--sm"
          :class="{ 'btn--on': menu }"
          :aria-expanded="menu"
          aria-haspopup="true"
          :aria-label="t('transcript.display')"
          :title="t('transcript.display')"
          @click="menu = !menu"
        >
          <PhSlidersHorizontal :size="17" />
        </button>
        <Transition name="pop">
          <div v-if="menu" class="menu" role="group" :aria-label="t('transcript.display')">
            <p class="menu__title">{{ t("transcript.display") }}</p>
            <SegmentedControl v-model="prefs.tView" :options="viewOptions" :label="t('transcript.viewLabel')" size="sm" />
            <SegmentedControl v-model="prefs.tDensity" :options="densityOptions" :label="t('transcript.densityLabel')" size="sm" />
            <label class="menu__row">
              <span>{{ t("transcript.size") }} <small class="mono">{{ prefs.tSize }}px</small></span>
              <input v-model.number="prefs.tSize" class="range" type="range" :min="T_SIZE.min" :max="T_SIZE.max" :step="T_SIZE.step" />
            </label>
            <label class="menu__row"><span>{{ t("transcript.times") }}</span><ToggleSwitch v-model="prefs.tTimes" /></label>
            <label class="menu__row"><span>{{ t("transcript.karaoke") }}</span><ToggleSwitch v-model="prefs.karaoke" /></label>
            <label class="menu__row"><span>{{ t("transcript.turns") }}</span><ToggleSwitch v-model="prefs.tTurns" /></label>
            <label class="menu__row"><span>{{ t("transcript.tags") }}</span><ToggleSwitch v-model="prefs.tTags" /></label>
          </div>
        </Transition>
      </div>
    </header>

    <div ref="box" class="tp__lines" @click="onClick" @scroll.passive="onScroll">
      <p v-if="!cues.length" class="tp__empty">{{ t("transcript.empty") }}</p>
      <p v-else-if="matches && !matches.size" class="tp__empty">{{ t("transcript.noMatch", { q }) }}</p>
      <template v-for="(c, i) in cues" :key="i">
        <button
          v-if="headAt(i)"
          type="button"
          class="chap"
          :class="{ on: headAt(i)!.k === curChapter }"
          :title="session.chapterSource === 'ai' ? t('transcript.chapterAi') : headAt(i)!.ch.src"
          :aria-label="t('transcript.chapter', { n: headAt(i)!.k + 1, title: headAt(i)!.ch.title })"
          @click.stop="seekTo(headAt(i)!.ch.start)"
        >
          <span class="chap__n mono">{{ formatTime(headAt(i)!.ch.start) }}</span>
          <span class="chap__t" dir="auto">{{ headAt(i)!.ch.title }}</span>
        </button>
        <div
          v-show="!matches || matches.has(i)"
          class="row"
          :class="[{ on: i === session.curIdx, editing: editing === i, turn: turns?.[i] }, who ? 'sp' + who[i] : '']"
          :style="i === session.curIdx ? { '--p': String(frac) } : undefined"
          :data-i="i"
        >
          <button v-if="prefs.tTimes" type="button" class="tm mono" :aria-label="t('transcript.seek', { time: formatTime(c.start) })" @click.stop="seekToCue(i)">
            {{ formatTime(c.start) }}
          </button>
          <div class="tx">
            <p v-if="showSrc" class="src" :class="{ main: !showTr }" :dir="srcDir" :lang="session.srcLang === 'auto' ? undefined : session.srcLang">
              <template v-if="needle">
                <template v-for="(p, k) in highlight(c.src, q)" :key="k"><mark v-if="p.hit">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template>
              </template>
              <template v-else>
                <template v-for="(part, k) in srcParts[i]" :key="k">
                  <span v-if="part.kind === 'tag'" class="snd" :class="part.sound" :title="part.label" :aria-label="part.label">
                    <component :is="SOUND_ICON[part.sound]" :size="13" weight="bold" />
                  </span>
                  <template v-else>
                    <template v-for="(tk, j) in part.tokens" :key="j"><span v-if="tk.word" class="w" :data-w="tk.lookup">{{ tk.text }}</span><template v-else>{{ tk.text }}</template></template>
                  </template>
                </template>
              </template>
            </p>
            <div v-if="editing === i" class="edit-box">
              <label class="sr-only" :for="'ed' + i">{{ t("transcript.editLabel") }}</label>
              <textarea :id="'ed' + i" ref="editor" v-model="draft" class="textarea" :dir="trDir" rows="2" @keydown="onEditKey"></textarea>
              <div class="edit-actions">
                <button type="button" class="btn btn--primary btn--sm" @click="saveEdit"><PhCheck :size="14" />{{ t("common.save") }}</button>
                <button type="button" class="btn btn--quiet btn--sm" @click="cancelEdit"><PhX :size="14" />{{ t("common.cancel") }}</button>
                <span class="hint">{{ t("transcript.editHint") }}</span>
              </div>
            </div>
            <p v-else-if="showTr" class="tr" :class="{ pending: !tr[i] }" :dir="trDir">
              <template v-if="needle && tr[i]">
                <template v-for="(p, k) in highlight(tr[i]!, q)" :key="k"><mark v-if="p.hit">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template>
              </template>
              <template v-else-if="i === session.curIdx && activeWords">
                <template v-for="(part, k) in activeWords" :key="k">
                  <span v-if="part.kind === 'tag'" class="snd" :class="part.sound" :title="part.label"><component :is="SOUND_ICON[part.sound]" :size="13" weight="bold" /></span>
                  <template v-else><span v-for="(x, j) in part.words" :key="j" class="kw" :class="{ lit: x.lit }">{{ x.w }}</span></template>
                </template>
              </template>
              <template v-else-if="tr[i]">
                <template v-for="(part, k) in trParts(i)" :key="k">
                  <span v-if="part.kind === 'tag'" class="snd" :class="part.sound" :title="part.label"><component :is="SOUND_ICON[part.sound]" :size="13" weight="bold" /></span>
                  <template v-else>{{ part.text }}</template>
                </template>
              </template>
              <span v-else class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
              <span v-if="edited.has(i)" class="edited">{{ t("transcript.edited") }}</span>
            </p>
          </div>
          <div v-if="editing !== i" class="acts">
            <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('transcript.loop')" :title="t('transcript.loop')" @click.stop="loopLine(i)">
              <PhRepeatOnce :size="15" />
            </button>
            <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('transcript.copy')" :title="t('transcript.copy')" @click.stop="copyLine(i)">
              <PhCopy :size="15" />
            </button>
            <button v-if="canEdit && c.src" type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('transcript.edit')" :title="t('transcript.edit')" @click.stop="startEdit(i)">
              <PhPencilSimple :size="15" />
            </button>
          </div>
          <i v-if="i === session.curIdx && prefs.karaoke" class="bar" aria-hidden="true"></i>
        </div>
      </template>
    </div>

    <Transition name="rise">
      <button v-if="away && prefs.follow && session.curIdx >= 0 && !needle" type="button" class="now btn btn--primary btn--sm" @click="backToNow">
        <PhArrowDown :size="15" />{{ t("transcript.backToNow") }}
      </button>
    </Transition>
  </section>
</template>

<style scoped>
.chap {
  display: flex;
  align-items: baseline;
  gap: var(--s-3);
  width: 100%;
  padding: var(--s-4) var(--s-4) var(--s-2);
  border: 0;
  border-top: 1px solid var(--line);
  background: transparent;
  color: var(--text);
  font: inherit;
  font-weight: 650;
  font-size: calc(var(--t-size) + 1px);
  text-align: start;
  cursor: pointer;
}
.chap:first-child {
  border-top: 0;
}
.chap:hover {
  background: var(--surface-2);
}
.chap:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}
.chap__n {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3);
}
.chap.on .chap__t {
  color: var(--accent-ink);
}
.chap.on .chap__n {
  color: var(--accent-ink);
}
.tp {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--surface-1);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  overflow: hidden;
  --t-size: 15px;
}
.tp__head {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-3) var(--s-4);
  border-bottom: 1px solid var(--line);
  z-index: 2;
}
.tp__title {
  font-size: var(--fs-md);
  font-weight: 600;
  flex: none;
}
.tp__search {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding-inline: 10px 6px;
  min-height: 36px;
  border-radius: var(--r-sm);
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--text-3);
}
.tp__search:focus-within {
  border-color: var(--accent-line);
}
.tp__search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  font-size: var(--fs-sm);
  min-height: 34px;
}
.count {
  font-size: var(--fs-xs);
  white-space: nowrap;
  color: var(--text-2);
}
.follow {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-xs);
  color: var(--text-2);
  cursor: pointer;
}
.menu-wrap {
  position: relative;
  flex: none;
}
.menu {
  position: absolute;
  inset-inline-end: 0;
  top: calc(100% + 8px);
  width: min(290px, 80vw);
  display: grid;
  gap: var(--s-2);
  padding: var(--s-3);
  border-radius: var(--r-md);
  background: var(--surface-1);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-2);
}
.menu__title {
  font-size: var(--fs-sm);
  font-weight: 600;
}
.menu__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-2);
  font-size: var(--fs-sm);
  cursor: pointer;
}
.menu__row .range {
  width: 120px;
}
.pop-enter-active,
.pop-leave-active {
  transition: opacity 140ms var(--ease), transform 140ms var(--ease);
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}
.tp__lines {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--s-2);
  overscroll-behavior: contain;
}
.tp__empty {
  padding: var(--s-8) var(--s-4);
  text-align: center;
  color: var(--text-2);
  font-size: var(--fs-sm);
}
.row {
  position: relative;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: start;
  gap: var(--s-2);
  padding: 8px 8px 8px 6px;
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background 200ms var(--ease);
  /* Long videos have thousands of lines: let the browser skip rendering the ones off screen. */
  content-visibility: auto;
  contain-intrinsic-size: auto 70px;
}
.notimes .row {
  grid-template-columns: minmax(0, 1fr);
}
.compact .row {
  padding-block: 4px;
  contain-intrinsic-size: auto 48px;
}
.row:hover {
  background: var(--surface-2);
}
.row.on {
  background: var(--accent-soft);
}
/* A new speaker: a little space before, and their colour on the edge. */
.row.turn {
  margin-top: 10px;
}
.row.sp0,
.row.sp1 {
  border-inline-start: 3px solid transparent;
}
.row.sp0 {
  border-inline-start-color: color-mix(in srgb, var(--lapis) 45%, transparent);
}
.row.sp1 {
  border-inline-start-color: color-mix(in srgb, var(--accent-strong) 55%, transparent);
}
/* The line being spoken gets the saffron diamond from the mark. */
.row.on::before {
  content: "";
  position: absolute;
  inset-inline-start: -3px;
  top: 15px;
  width: 7px;
  height: 7px;
  border-radius: 1px;
  transform: rotate(45deg);
  background: var(--accent-strong);
}
/* ...and fills as it is spoken. */
.bar {
  position: absolute;
  inset-inline-start: 8px;
  bottom: 3px;
  height: 2px;
  width: calc((100% - 16px) * var(--p, 0));
  border-radius: 2px;
  background: linear-gradient(90deg, var(--accent-strong), var(--accent));
  transition: width 260ms linear;
}
.tm {
  align-self: start;
  justify-self: start;
  margin-top: 1px;
  padding: 2px 6px;
  border: 0;
  border-radius: var(--r-xs);
  background: transparent;
  color: var(--text-3);
  font-size: 12px;
  direction: ltr;
}
.tm:hover {
  color: var(--text);
  background: var(--surface-3);
}
.row.on .tm {
  color: var(--accent-ink);
}
.tx {
  display: grid;
  gap: 3px;
  min-width: 0;
}
.src {
  color: var(--text-2);
  font-size: calc(var(--t-size) * 0.88);
  line-height: 1.55;
  text-align: left;
}
.src[dir="rtl"] {
  text-align: right;
}
.src.main {
  color: var(--text);
  font-size: var(--t-size);
}
.tr {
  font-size: var(--t-size);
  line-height: 1.75;
  font-weight: 450;
}
.compact .tr,
.compact .src {
  line-height: 1.45;
}
.tr[dir="ltr"] {
  text-align: left;
}
.tr.pending {
  color: var(--text-3);
}
/* Words light up in turn while the line is said. */
.kw {
  transition: color 220ms var(--ease);
}
.row.on .kw {
  color: var(--text-3);
}
.row.on .kw.lit {
  color: var(--text);
}
.snd {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 18px;
  margin-inline: 2px;
  vertical-align: -3px;
  border-radius: var(--r-pill);
  background: var(--surface-3);
  color: var(--text-2);
}
.snd.music {
  color: var(--accent-ink);
  background: var(--accent-soft);
}
.row.on .snd.music svg {
  animation: bob 1.2s ease-in-out infinite;
}
@keyframes bob {
  50% {
    transform: translateY(-2px);
  }
}
.dots {
  display: inline-flex;
  gap: 3px;
  vertical-align: middle;
}
.dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-3);
  animation: blink 1.2s ease-in-out infinite;
}
.dots i:nth-child(2) {
  animation-delay: 0.2s;
}
.dots i:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  50% {
    opacity: 0.25;
  }
}
.edited {
  margin-inline-start: 8px;
  font-size: 11px;
  color: var(--accent-ink);
  border: 1px solid var(--accent-line);
  border-radius: var(--r-pill);
  padding: 0 6px;
  vertical-align: 2px;
}
.w {
  border-radius: 3px;
  cursor: help;
}
.w:hover {
  background: var(--accent-soft);
  color: var(--text);
  box-shadow: 0 1px 0 var(--accent-line);
}
mark {
  background: color-mix(in srgb, var(--accent) 40%, transparent);
  color: inherit;
  border-radius: 3px;
  padding: 0 1px;
}
/* The line's buttons float over its end corner, so they never take room from the text. */
.acts {
  position: absolute;
  top: 4px;
  inset-inline-end: 4px;
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: var(--r-sm);
  background: var(--surface-1);
  box-shadow: var(--shadow-1, 0 2px 8px rgba(0, 0, 0, 0.12));
  opacity: 0;
  pointer-events: none;
  transform: translateY(-2px);
  transition: opacity 150ms var(--ease), transform 150ms var(--ease);
}
.row:hover .acts,
.row:focus-within .acts {
  opacity: 1;
  pointer-events: auto;
  transform: none;
}
@media (hover: none) {
  .row.on .acts {
    opacity: 1;
    pointer-events: auto;
    transform: none;
  }
}
.edit-box {
  display: grid;
  gap: 8px;
  cursor: auto;
}
.edit-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.hint {
  font-size: var(--fs-xs);
  color: var(--text-3);
}
.now {
  position: absolute;
  bottom: var(--s-4);
  left: 50%;
  transform: translateX(-50%);
  box-shadow: var(--shadow-2);
  z-index: 3;
}
.rise-enter-active,
.rise-leave-active {
  transition: opacity 180ms var(--ease), transform 180ms var(--ease);
}
.rise-enter-from,
.rise-leave-to {
  opacity: 0;
  transform: translate(-50%, 10px);
}
@media (prefers-reduced-motion: reduce) {
  .bar,
  .kw,
  .row {
    transition: none;
  }
  .row.on .snd.music svg,
  .dots i {
    animation: none;
  }
}
</style>
