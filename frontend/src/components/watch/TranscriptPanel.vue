<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { PhCheck, PhMagnifyingGlass, PhPencilSimple, PhX } from "@phosphor-icons/vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { openLookup } from "@/composables/lookup";
import { usePrefs } from "@/composables/prefs";
import { cues, editLine, edited, seekToCue, session, tr } from "@/composables/session";
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

/* Tokens are computed once per cue list; the source text never changes. */
const tokens = computed(() => cues.value.map((c) => tokenize(c.src)));

/* Keep the line being spoken in view, a third of the way down, unless the user is searching or editing. */
watch(
  () => session.curIdx,
  async (i) => {
    if (i < 0 || !prefs.follow || needle.value || editing.value >= 0) return;
    await nextTick();
    const el = box.value?.querySelector<HTMLElement>(`[data-i="${i}"]`);
    const b = box.value;
    if (!el || !b) return;
    const top = el.offsetTop - b.clientHeight / 3;
    if (Math.abs(b.scrollTop - top) > 40) b.scrollTo({ top, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  },
);

function onClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  const row = target.closest<HTMLElement>("[data-i]");
  if (!row || target.closest(".edit-box, .edit-btn")) return;
  const i = Number(row.dataset.i);
  const w = target.closest<HTMLElement>(".w");
  if (w) return void openLookup(w.dataset.w || w.textContent || "", i, w);
  seekToCue(i);
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

defineExpose({ focusSearch: () => search.value?.focus() });
</script>

<template>
  <section class="tp" :aria-label="t('transcript.title')">
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
    </header>

    <div ref="box" class="tp__lines" @click="onClick">
      <p v-if="!cues.length" class="tp__empty">{{ t("transcript.empty") }}</p>
      <p v-else-if="matches && !matches.size" class="tp__empty">{{ t("transcript.noMatch", { q }) }}</p>
      <template v-for="(c, i) in cues" :key="i">
        <div
          v-show="!matches || matches.has(i)"
          class="row"
          :class="{ on: i === session.curIdx, editing: editing === i }"
          :data-i="i"
        >
          <button type="button" class="tm mono" :aria-label="t('transcript.seek', { time: formatTime(c.start) })" @click.stop="seekToCue(i)">
            {{ formatTime(c.start) }}
          </button>
          <div class="tx">
            <p class="src" :dir="srcDir" :lang="session.srcLang === 'auto' ? undefined : session.srcLang">
              <template v-if="needle">
                <template v-for="(p, k) in highlight(c.src, q)" :key="k"><mark v-if="p.hit">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template>
              </template>
              <template v-else>
                <template v-for="(tk, k) in tokens[i]" :key="k"><span v-if="tk.word" class="w" :data-w="tk.lookup">{{ tk.text }}</span><template v-else>{{ tk.text }}</template></template>
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
            <p v-else-if="!session.sameLang" class="tr" :class="{ pending: !tr[i] }" :dir="trDir">
              <template v-if="needle && tr[i]">
                <template v-for="(p, k) in highlight(tr[i]!, q)" :key="k"><mark v-if="p.hit">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template>
              </template>
              <template v-else>{{ tr[i] || "…" }}</template>
              <span v-if="edited.has(i)" class="edited">{{ t("transcript.edited") }}</span>
            </p>
          </div>
          <button v-if="canEdit && c.src && editing !== i" type="button" class="edit-btn btn btn--quiet btn--icon btn--sm" :aria-label="t('transcript.edit')" :title="t('transcript.edit')" @click.stop="startEdit(i)">
            <PhPencilSimple :size="15" />
          </button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.tp {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: var(--surface-1);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  overflow: hidden;
}
.tp__head {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-3) var(--s-4);
  border-bottom: 1px solid var(--line);
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
  grid-template-columns: 56px minmax(0, 1fr) 34px;
  gap: var(--s-2);
  padding: 8px 8px 8px 6px;
  border-radius: var(--r-sm);
  cursor: pointer;
  /* Long videos have thousands of lines: let the browser skip rendering the ones off screen. */
  content-visibility: auto;
  contain-intrinsic-size: auto 70px;
}
.row:hover {
  background: var(--surface-2);
}
.row.on {
  background: var(--accent-soft);
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
  font-size: 13.5px;
  line-height: 1.55;
  text-align: left;
}
.tr {
  font-size: 15.5px;
  line-height: 1.75;
  font-weight: 450;
}
.tr[dir="ltr"] {
  text-align: left;
}
.tr.pending {
  color: var(--text-3);
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
.edit-btn {
  align-self: start;
  opacity: 0;
}
.row:hover .edit-btn,
.edit-btn:focus-visible,
.row.on .edit-btn {
  opacity: 1;
}
@media (hover: none) {
  .edit-btn {
    opacity: 0.7;
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
</style>
