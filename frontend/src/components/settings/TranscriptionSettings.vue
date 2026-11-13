<script setup lang="ts">
/* Settings -> Transcription: what this computer can run, the model it should use and why, and every
   choice that changes accuracy, each with its cost. */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhCheckCircle, PhCpu, PhDownloadSimple, PhGraphicsCard, PhMemory, PhSparkle, PhTrash, PhWarning } from "@phosphor-icons/vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api } from "@/api/client";
import type { AsrSettings, AsrState } from "@/api/types";
import { toast } from "@/composables/toast";

const { t, te } = useI18n();
const st = ref<AsrState | null>(null);
const remote = ref(false);
const saving = ref(false);
let timer: number | undefined;

async function load() {
  try {
    st.value = await api.asr();
    vocab.value = st.value.settings.vocab || "";
    watchLoading();
  } catch {
    remote.value = true;
  }
}

async function set(change: Partial<AsrSettings>) {
  if (!st.value) return;
  const before = { ...st.value.settings };
  Object.assign(st.value.settings, change);
  saving.value = true;
  try {
    st.value = await api.setAsr(change);
  } catch {
    st.value.settings = before;
    toast(t("errors.UNKNOWN"), { tone: "danger" });
  } finally {
    saving.value = false;
  }
}

/* Deleting a downloaded model takes two clicks: the first arms the button for a few seconds. */
const armed = ref("");
const deleting = ref("");
let disarm: number | undefined;
async function remove(id: string) {
  if (armed.value !== id) {
    armed.value = id;
    window.clearTimeout(disarm);
    disarm = window.setTimeout(() => (armed.value = ""), 4000);
    return;
  }
  armed.value = "";
  deleting.value = id;
  try {
    const r = await api.deleteAsrModel(id);
    st.value = r;
    toast(t("asrSet.deleted", { model: id, size: sizeLabel(Math.round(r.freed / 1_000_000)) }), { tone: "ok" });
  } catch (e) {
    toast((e as Error).message || t("errors.UNKNOWN"), { tone: "danger" });
  } finally {
    deleting.value = "";
  }
}

/* What the names list fixes, with words anyone may use (never the user's own names). */
const vocabExamples = [
  ["إكسيل", "Excel"],
  ["زووم", "Zoom"],
  ["باور بوينت", "PowerPoint"],
  ["واتس اب", "WhatsApp"],
] as const;

/* The list of names is saved when the field is left, not on every key. */
const vocab = ref("");
function saveVocab() {
  if (st.value && vocab.value !== st.value.settings.vocab) void set({ vocab: vocab.value });
}

async function prepare() {
  try {
    st.value = await api.prepareAsr();
    watchLoading(true);
  } catch {
    toast(t("errors.UNKNOWN"), { tone: "danger" });
  }
}

/** While a model downloads, the page follows it. */
function watchLoading(force = false) {
  clearInterval(timer);
  if (!force && !st.value?.status.loading) return;
  let quiet = 0;
  timer = window.setInterval(async () => {
    try {
      st.value = await api.asr();
    } catch {
      return;
    }
    quiet = st.value.status.loading ? 0 : quiet + 1;
    if (quiet > 2) clearInterval(timer);
  }, 1500);
}

onMounted(load);
onBeforeUnmount(() => {
  clearInterval(timer);
  window.clearTimeout(disarm);
});

const hw = computed(() => st.value?.hardware);
const rec = computed(() => st.value?.recommended);
const eff = computed(() => st.value?.effective);
const gpuState = computed(() => {
  const h = hw.value;
  if (!h?.cuda) return { ok: false, text: t("asrSet.gpuNone") };
  if (h.gpuOld) return { ok: false, text: t("asrSet.gpuOld") };
  if (!h.cublas) return { ok: false, text: t("asrSet.gpuNoCuda") };
  return { ok: true, text: t("asrSet.gpuReady") };
});

const langLabel = (c: string) => (c === "auto" ? t("asrSet.langAuto") : te("langs." + c) ? t("langs." + c) : c);
const sizeLabel = (mb: number) => (mb >= 1000 ? t("asrSet.gb", { n: (mb / 1000).toFixed(1) }) : t("asrSet.mb", { n: mb }));
const qualityOptions = computed(() => [
  { value: "accurate" as const, label: t("asrSet.accurate") },
  { value: "fast" as const, label: t("asrSet.fast") },
]);
const deviceOptions = computed(() => [
  { value: "auto" as const, label: t("asrSet.deviceAuto") },
  { value: "cpu" as const, label: t("asrSet.cpu") },
  { value: "cuda" as const, label: t("asrSet.gpu") },
]);

const status = computed(() => {
  const s = st.value?.status;
  if (!s) return "";
  if (!s.installed) return t("asrSet.notInstalled");
  if (s.loading) return s.loading.progress != null ? t("asrSet.downloading", { model: s.loading.model, pct: s.loading.progress }) : t("asrSet.loading", { model: s.loading.model });
  if (s.ready) return t("asrSet.ready", { model: s.model, device: t(s.device === "cuda" ? "asrSet.gpu" : "asrSet.cpu") });
  const m = st.value?.models.find((x) => x.id === eff.value?.model);
  return m?.downloaded ? t("asrSet.onDisk", { model: m.id }) : t("asrSet.notYet", { model: eff.value?.model, size: m ? sizeLabel(m.size) : "" });
});
</script>

<template>
  <div class="asr">
    <p class="panel__lead">{{ t("asrSet.lead") }}</p>
    <p v-if="remote" class="muted">{{ t("phone.remote") }}</p>

    <template v-else-if="st && hw && rec && eff">
      <!-- this computer -->
      <div class="machine" role="group" :aria-label="t('asrSet.machine')">
        <div class="fact">
          <PhCpu :size="20" />
          <span>
            <b>{{ t("asrSet.cpuFact", { n: hw.threads }) }}</b>
            <small v-if="hw.cores">{{ t("asrSet.cores", { n: hw.cores }) }}</small>
          </span>
        </div>
        <div class="fact">
          <PhMemory :size="20" />
          <span>
            <b>{{ t("asrSet.ramFact", { n: hw.ramGb }) }}</b>
            <small>{{ t("asrSet.ram") }}</small>
          </span>
        </div>
        <div class="fact" :class="{ off: !gpuState.ok }">
          <PhGraphicsCard :size="20" />
          <span>
            <b>{{ hw.gpu || (hw.cuda ? "NVIDIA" : t("asrSet.noGpu")) }}<template v-if="hw.vramGb"> · {{ t("asrSet.ramFact", { n: hw.vramGb }) }}</template></b>
            <small>{{ gpuState.text }}</small>
          </span>
        </div>
      </div>

      <!-- the recommendation and why -->
      <div class="rec">
        <p class="rec__head">
          <PhCheckCircle :size="20" weight="fill" />
          <span>
            {{ t("asrSet.recommended") }}
            <b dir="ltr">{{ rec.model }}</b>
            {{ t(rec.device === "cuda" ? "asrSet.onGpu" : "asrSet.onCpu") }}
          </span>
        </p>
        <ul>
          <li v-for="(w, i) in rec.why" :key="i">{{ w }}</li>
        </ul>
      </div>

      <!-- the model -->
      <fieldset class="models">
        <legend class="sub">{{ t("asrSet.model") }}</legend>
        <label class="model" :class="{ on: st.settings.model === 'auto' }">
          <input type="radio" name="asr-model" value="auto" :checked="st.settings.model === 'auto'" :disabled="saving" @change="set({ model: 'auto' })" />
          <span class="m-name">{{ t("asrSet.auto") }}</span>
          <span class="m-hint">{{ rec.short && rec.short !== rec.model ? t("asrSet.autoHintShort", { model: rec.model, short: rec.short }) : t("asrSet.autoHint", { model: rec.model }) }}</span>
        </label>
        <label v-for="m in st.models" :key="m.id" class="model" :class="{ on: st.settings.model === m.id }">
          <input type="radio" name="asr-model" :value="m.id" :checked="st.settings.model === m.id" :disabled="saving" @change="set({ model: m.id })" />
          <span class="m-name" dir="ltr">{{ m.id }}</span>
          <span class="m-tags">
            <span v-if="m.id === rec.model" class="chip chip--ok">{{ t("asrSet.tagRec") }}</span>
            <span v-else-if="m.id === rec.short" class="chip chip--accent">{{ t("asrSet.tagShort") }}</span>
            <span v-if="m.downloaded" class="chip">{{ t("asrSet.tagDown") }}</span>
          </span>
          <span class="m-acc" :aria-label="t('asrSet.accuracy', { n: m.ar })" :title="t('asrSet.accuracy', { n: m.ar })">
            <i v-for="k in 5" :key="k" :class="{ lit: k <= m.ar }"></i>
          </span>
          <span class="m-meta">{{ t("asrSet.speed", { n: m.secondsPerMinute }) }} · {{ sizeLabel(m.downloaded && m.diskMb ? m.diskMb : m.size) }}</span>
          <span v-if="m.warning" class="m-warn"><PhWarning :size="14" />{{ m.warning }}</span>
          <button
            v-if="m.downloaded"
            type="button"
            class="m-del"
            :class="{ armed: armed === m.id }"
            :disabled="deleting === m.id"
            :aria-label="t('asrSet.delete', { model: m.id })"
            @click.prevent.stop="remove(m.id)"
          >
            <PhTrash :size="15" />
            <span v-if="armed === m.id">{{ t("asrSet.deleteConfirm") }}</span>
          </button>
        </label>
      </fieldset>

      <div class="prep">
        <span class="muted">{{ status }}</span>
        <button
          v-if="st.status.installed && !st.status.ready && !st.status.loading && !st.models.find((x) => x.id === eff?.model)?.downloaded"
          class="btn btn--outline btn--sm"
          type="button"
          @click="prepare"
        >
          <PhDownloadSimple :size="16" />
          {{ t("asrSet.prepare") }}
        </button>
      </div>
      <p v-if="st.status.fallback" class="notice notice--danger"><PhWarning :size="18" />{{ st.status.fallback }}</p>

      <!-- language and how Arabic is written -->
      <div class="opt">
        <label class="opt__label" for="asr-lang">
          {{ t("asrSet.language") }}
          <small>{{ t("asrSet.languageHint") }}</small>
        </label>
        <select id="asr-lang" class="select sel" :value="st.settings.language" :disabled="saving" @change="set({ language: ($event.target as HTMLSelectElement).value })">
          <option v-for="c in st.languages" :key="c" :value="c">{{ langLabel(c) }}</option>
        </select>
      </div>
      <div class="opt">
        <label class="opt__label" for="asr-style">
          {{ t("asrSet.style") }}
          <small>{{ t("asrSet.styleHint") }}</small>
        </label>
        <select id="asr-style" class="select sel" :value="st.settings.style" :disabled="saving" @change="set({ style: ($event.target as HTMLSelectElement).value as AsrSettings['style'] })">
          <option v-for="s in st.styles" :key="s" :value="s">{{ t("asrSet.styles." + s) }}</option>
        </select>
      </div>
      <div class="opt opt--stack">
        <label class="opt__label" for="asr-vocab">
          {{ t("asrSet.vocab") }}
          <small>{{ t("asrSet.vocabHint") }}</small>
        </label>
        <textarea
          id="asr-vocab"
          v-model="vocab"
          class="input vocab"
          rows="3"
          maxlength="600"
          :dir="vocab ? 'auto' : undefined"
          :placeholder="t('asrSet.vocabPlaceholder')"
          @blur="saveVocab"
        ></textarea>
        <table class="vocab-ex">
          <caption>{{ t("asrSet.vocabExTitle") }}</caption>
          <thead>
            <tr>
              <th scope="col">{{ t("asrSet.vocabExHeard") }}</th>
              <th scope="col">{{ t("asrSet.vocabExWrite") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in vocabExamples" :key="i">
              <td>{{ row[0] }}</td>
              <td dir="auto"><code>{{ row[1] }}</code></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="opt">
        <label class="opt__label" for="asr-ai">
          <span class="ai-label"><PhSparkle :size="16" />{{ t("asrSet.aiFix") }}</span>
          <small>{{ t("asrSet.aiFixHint") }}</small>
          <small v-if="!st.aiReady" class="need-ai">
            {{ t("asrSet.aiFixNeedsAi") }}
            <a href="#ai">{{ t("asrSet.aiFixSetup") }}</a>
          </small>
        </label>
        <ToggleSwitch id="asr-ai" :model-value="st.settings.aiFix && st.aiReady" :disabled="saving || !st.aiReady" @update:model-value="set({ aiFix: $event })" />
      </div>
      <div class="opt">
        <span class="opt__label">
          {{ t("asrSet.quality") }}
          <small>{{ t("asrSet.qualityHint") }}</small>
        </span>
        <SegmentedControl :model-value="st.settings.quality" :options="qualityOptions" :label="t('asrSet.quality')" @update:model-value="set({ quality: $event })" />
      </div>
      <div class="opt">
        <label class="opt__label" for="asr-enhance">
          {{ t("asrSet.enhance") }}
          <small>{{ t("asrSet.enhanceHint") }}</small>
        </label>
        <ToggleSwitch id="asr-enhance" :model-value="st.settings.enhance" :disabled="saving" @update:model-value="set({ enhance: $event })" />
      </div>
      <div class="opt">
        <label class="opt__label" for="asr-vad">
          {{ t("asrSet.vad") }}
          <small>{{ t("asrSet.vadHint") }}</small>
        </label>
        <ToggleSwitch id="asr-vad" :model-value="st.settings.vad" :disabled="saving" @update:model-value="set({ vad: $event })" />
      </div>
      <div class="opt">
        <span class="opt__label">
          {{ t("asrSet.device") }}
          <small>{{ gpuState.ok ? t("asrSet.deviceHint") : gpuState.text }}</small>
        </span>
        <SegmentedControl :model-value="st.settings.device" :options="deviceOptions" :label="t('asrSet.device')" @update:model-value="set({ device: $event })" />
      </div>

      <p class="honest">{{ t("asrSet.honest") }}</p>
    </template>
  </div>
</template>

<style scoped>
.machine {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--s-2);
  margin: var(--s-3) 0;
}
.fact {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: var(--s-3);
  border-radius: var(--r-md);
  background: var(--surface-2);
  border: 1px solid var(--line);
  min-width: 0;
}
.fact svg {
  flex: none;
  margin-top: 2px;
  color: var(--accent-ink);
}
.fact.off svg {
  color: var(--ink-3, #8a90b8);
}
.fact span {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.fact b {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.fact small {
  color: var(--ink-2, inherit);
  opacity: 0.8;
  font-size: var(--fs-xs);
  line-height: 1.5;
}
.rec {
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r-md);
  border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  margin-bottom: var(--s-4);
}
.rec__head {
  display: flex;
  gap: 8px;
  align-items: center;
  font-weight: 600;
}
.rec__head svg {
  color: var(--accent-ink);
  flex: none;
}
.rec ul {
  margin: var(--s-2) 0 0;
  padding-inline-start: 1.6em;
  display: grid;
  gap: 4px;
  font-size: var(--fs-sm);
}
.models {
  /* A fieldset is as wide as its content by default: it must shrink with the page. */
  min-width: 0;
  border: 0;
  padding: 0;
  margin: 0 0 var(--s-2);
  display: grid;
  gap: 6px;
}
.sub {
  font-weight: 600;
  margin-bottom: var(--s-2);
}
.model {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  grid-template-areas:
    "radio name tags acc"
    "radio meta meta del"
    "radio warn warn warn";
  column-gap: 10px;
  row-gap: 2px;
  align-items: center;
  padding: 10px var(--s-3);
  border-radius: var(--r-md);
  border: 1px solid var(--line);
  cursor: pointer;
  transition: border-color 150ms var(--ease), background 150ms var(--ease);
}
.model:hover {
  background: var(--surface-2);
}
.model.on {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 7%, transparent);
}
.model input {
  grid-area: radio;
  accent-color: var(--accent-strong);
  width: 18px;
  height: 18px;
}
.m-name {
  grid-area: name;
  font-weight: 600;
}
.m-hint {
  grid-area: meta;
  font-size: var(--fs-xs);
  opacity: 0.8;
}
.m-tags {
  grid-area: tags;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}
.m-acc {
  grid-area: acc;
  display: flex;
  gap: 3px;
}
.m-acc i {
  width: 14px;
  height: 6px;
  border-radius: 3px;
  background: var(--surface-3);
}
.m-acc i.lit {
  background: var(--accent);
}
.m-meta {
  grid-area: meta;
  font-size: var(--fs-xs);
  opacity: 0.8;
  font-variant-numeric: tabular-nums;
}
.m-warn {
  grid-area: warn;
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: var(--fs-xs);
  color: var(--danger, #ff9a9a);
}
.m-del {
  grid-area: del;
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--r-pill);
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  opacity: 0.7;
  font: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.m-del:hover {
  opacity: 1;
  background: var(--surface-2);
}
.m-del.armed {
  opacity: 1;
  color: var(--danger, #e5484d);
  border-color: currentColor;
}
.m-del:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.vocab {
  width: 100%;
  min-height: 72px;
  resize: vertical;
  font: inherit;
}
.vocab-ex {
  align-self: flex-start;
  justify-self: start;
  margin-top: var(--s-2);
  border-collapse: collapse;
  font-size: var(--fs-xs);
  width: 100%;
  max-width: 420px;
}
.vocab-ex caption {
  text-align: start;
  padding-bottom: 4px;
  opacity: 0.8;
}
.vocab-ex th,
.vocab-ex td {
  text-align: start;
  padding: 5px 10px;
  border-bottom: 1px solid var(--line);
}
.vocab-ex th {
  font-weight: 600;
  background: var(--surface-2);
}
.vocab-ex code {
  font-family: inherit;
  font-weight: 600;
  color: var(--accent-ink);
}
.ai-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ai-label svg {
  color: var(--accent-ink);
}
.need-ai a {
  color: var(--accent-ink);
  text-decoration: underline;
}
.prep {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-2);
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--s-4);
  font-size: var(--fs-sm);
}
.sel {
  min-width: 190px;
}
.honest {
  margin-top: var(--s-4);
  font-size: var(--fs-sm);
  opacity: 0.85;
  line-height: 1.8;
}
@media (max-width: 640px) {
  .machine {
    grid-template-columns: 1fr;
  }
  .model {
    grid-template-columns: auto 1fr auto;
    grid-template-areas:
      "radio name acc"
      "radio tags tags"
      "radio meta del"
      "radio warn warn";
  }
  .sel {
    min-width: 0;
    width: 100%;
  }
}
</style>
