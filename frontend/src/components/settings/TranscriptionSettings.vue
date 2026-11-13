<script setup lang="ts">
/* Settings -> Transcription: what this computer can run, the model it should use and why, and every
   choice that changes accuracy, each with its cost. */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhCheckCircle, PhCpu, PhDownloadSimple, PhGraphicsCard, PhMagnifyingGlass, PhMemory, PhPlus, PhSparkle, PhTrash, PhWarning, PhX } from "@phosphor-icons/vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api } from "@/api/client";
import type { AsrSettings, AsrState, AsrUse, CustomModelInfo } from "@/api/types";
import { toast } from "@/composables/toast";

const { t, te } = useI18n();
const st = ref<AsrState | null>(null);
const remote = ref(false);
const saving = ref(false);
let timer: number | undefined;

async function load() {
  try {
    st.value = await api.asr();
    loadTerms();
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
  const custom = st.value?.models.find((m) => m.id === id)?.custom;
  try {
    const r = custom ? await api.removeCustomModel(id) : await api.deleteAsrModel(id);
    st.value = r;
    const name = st.value.models.find((m) => m.id === id)?.name || id.split(/[\\/]/).pop() || id;
    toast(
      r.freed ? t("asrSet.deleted", { model: name, size: sizeLabel(Math.round(r.freed / 1_000_000)) }) : t("asrSet.removed", { model: name }),
      { tone: "ok" },
    );
  } catch (e) {
    toast((e as Error).message || t("errors.UNKNOWN"), { tone: "danger" });
  } finally {
    deleting.value = "";
  }
}

/* Another model: a Hugging Face repository or a folder, looked at before it is added. */
const otherOpen = ref(false);
const source = ref("");
const checking = ref(false);
const found = ref<CustomModelInfo | null>(null);
const otherError = ref("");
const addFor = ref<AsrUse[]>(["audio"]);
async function checkOther() {
  if (!source.value.trim()) return;
  checking.value = true;
  found.value = null;
  otherError.value = "";
  try {
    found.value = (await api.checkCustomModel(source.value.trim())).model;
  } catch (e) {
    otherError.value = (e as Error).message || t("errors.UNKNOWN");
  } finally {
    checking.value = false;
  }
}
async function addOther() {
  if (!found.value) return;
  checking.value = true;
  try {
    st.value = await api.addCustomModel(found.value.id, addFor.value);
    toast(t("asrSet.otherAdded", { model: found.value.name }), { tone: "ok" });
    found.value = null;
    source.value = "";
    otherOpen.value = false;
  } catch (e) {
    otherError.value = (e as Error).message || t("errors.UNKNOWN");
  } finally {
    checking.value = false;
  }
}

/* A model for each use. */
const USES: AsrUse[] = ["audio", "video", "live"];
function autoFor(use: AsrUse): string {
  const r = st.value?.recommended;
  if (!r) return "";
  if (use === "live") return r.live;
  if (use === "audio") return r.short !== r.model ? t("asrSet.autoAudio", { short: r.short, model: r.model }) : r.short;
  return r.model;
}
function modelLabel(id: string): string {
  const m = st.value?.models.find((x) => x.id === id);
  return m?.custom ? m.name || id : id;
}
function setUse(use: AsrUse, model: string) {
  if (!st.value) return;
  void set({ models: { ...st.value.settings.models, [use]: model } });
}
function usedFor(id: string): AsrUse[] {
  return USES.filter((u) => st.value?.uses[u]?.model === id);
}

/* Words in the user's recordings, as rows like the pronunciation dictionary: what Whisper writes
   (optional) -> how it should be written. Saved with the button. */
let seq = 0;
type TermRow = { from: string; to: string; key: number };
const terms = ref<TermRow[]>([]);
const termRow = (r = { from: "", to: "" }): TermRow => ({ ...r, key: ++seq });
function loadTerms() {
  terms.value = (st.value?.settings.terms || []).map(termRow);
  if (!terms.value.length) terms.value.push(termRow());
}
async function addTerm() {
  terms.value.push(termRow());
  await Promise.resolve();
  const inputs = document.querySelectorAll<HTMLInputElement>(".terms .t-from");
  inputs[inputs.length - 1]?.focus();
}
async function saveTerms() {
  const list = terms.value.map((r) => ({ from: r.from.trim(), to: r.to.trim() })).filter((r) => r.to);
  await set({ terms: list });
  loadTerms();
  toast(t("asrSet.termsSaved"), { tone: "ok" });
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
      <div class="uses" role="group" :aria-label="t('asrSet.uses')">
        <p class="sub">{{ t("asrSet.uses") }}</p>
        <div v-for="u in USES" :key="u" class="use">
          <label class="use__label" :for="'asr-use-' + u">
            {{ t("asrSet.use." + u) }}
            <small>{{ t("asrSet.useHint." + u) }}</small>
          </label>
          <select
            :id="'asr-use-' + u"
            class="select use__select"
            :value="st.settings.models[u]"
            :disabled="saving"
            @change="setUse(u, ($event.target as HTMLSelectElement).value)"
          >
            <option value="auto">{{ t("asrSet.autoIs", { model: autoFor(u) }) }}</option>
            <option v-for="m in st.models" :key="m.id" :value="m.id">{{ modelLabel(m.id) }}{{ m.arabicOnly ? " — " + t("asrSet.tagArabic") : "" }}</option>
          </select>
          <small class="use__now">{{ t("asrSet.useNow", { model: modelLabel(st.uses[u].model), n: st.uses[u].secondsPerMinute }) }}</small>
        </div>
        <p class="muted small-note">{{ st.keepInMemory > 1 ? t("asrSet.twoInMemory") : t("asrSet.oneInMemory") }}</p>
      </div>

      <fieldset class="models">
        <legend class="sub">{{ t("asrSet.model") }}</legend>
        <div v-for="m in st.models" :key="m.id" class="model" :class="{ on: usedFor(m.id).length }">
          <span class="m-name" dir="ltr" :title="m.custom ? m.id : undefined">{{ m.custom ? m.name : m.id }}</span>
          <span class="m-tags">
            <span v-for="u in usedFor(m.id)" :key="u" class="chip chip--ok">{{ t("asrSet.usedFor." + u) }}</span>
            <span v-if="m.arabicOnly" class="chip">{{ t("asrSet.tagArabic") }}</span>
            <span v-if="m.custom" class="chip chip--accent">{{ m.kind === "dir" ? t("asrSet.tagFolder") : t("asrSet.tagCustom") }}</span>
            <span v-if="m.downloaded" class="chip">{{ t("asrSet.tagDown") }}</span>
          </span>
          <span v-if="m.ar" class="m-acc" :aria-label="t('asrSet.accuracy', { n: m.ar })" :title="t('asrSet.accuracy', { n: m.ar })">
            <i v-for="k in 5" :key="k" :class="{ lit: k <= m.ar }"></i>
          </span>
          <span v-else class="m-acc m-unknown">{{ t("asrSet.accuracyUnknown") }}</span>
          <span class="m-meta">
            {{ t(m.custom ? "asrSet.speedGuess" : "asrSet.speed", { n: m.secondsPerMinute }) }} · {{ sizeLabel(m.downloaded && m.diskMb ? m.diskMb : m.size) }}
            <template v-if="m.license"> · {{ t("asrSet.license", { name: m.license }) }}</template>
          </span>
          <span v-if="m.warning" class="m-warn"><PhWarning :size="14" />{{ m.warning }}</span>
          <button
            v-if="m.downloaded || m.custom"
            type="button"
            class="m-del"
            :class="{ armed: armed === m.id }"
            :disabled="deleting === m.id"
            :aria-label="t('asrSet.delete', { model: m.id })"
            @click.prevent.stop="remove(m.id)"
          >
            <PhTrash :size="15" />
            <span v-if="armed === m.id">{{ m.custom && m.kind === "dir" ? t("asrSet.removeConfirm") : t("asrSet.deleteConfirm") }}</span>
          </button>
        </div>

        <!-- another model, of the user's choice -->
        <button v-if="!otherOpen" type="button" class="btn btn--outline btn--sm other-open" @click="otherOpen = true">
          <PhPlus :size="15" />{{ t("asrSet.other") }}
        </button>
        <div v-else class="other">
          <p class="other__lead">{{ t("asrSet.otherLead") }}</p>
          <div class="other__row">
            <input
              v-model="source"
              class="input"
              dir="ltr"
              spellcheck="false"
              :placeholder="t('asrSet.otherPh')"
              :aria-label="t('asrSet.other')"
              @keydown.enter.prevent="checkOther"
            />
            <button type="button" class="btn btn--outline" :disabled="checking || !source.trim()" @click="checkOther">
              <PhMagnifyingGlass :size="16" />{{ checking && !found ? t("asrSet.otherChecking") : t("asrSet.otherCheck") }}
            </button>
          </div>
          <p v-if="otherError" class="notice notice--danger" role="alert"><PhWarning :size="18" />{{ otherError }}</p>
          <div v-if="found" class="found" role="status">
            <p class="found__name" dir="ltr">{{ found.name }}</p>
            <p class="found__meta">
              {{ found.kind === "dir" ? t("asrSet.otherOnDisk") : t("asrSet.otherDownload", { size: sizeLabel(found.sizeMb) }) }}
              <template v-if="found.license"> · {{ t("asrSet.license", { name: found.license }) }}</template>
            </p>
            <p class="found__warn"><PhWarning :size="14" />{{ t("asrSet.otherWarn") }}</p>
            <fieldset class="add-for">
              <legend>{{ t("asrSet.otherFor") }}</legend>
              <label v-for="u in USES" :key="u"><input v-model="addFor" type="checkbox" :value="u" />{{ t("asrSet.use." + u) }}</label>
            </fieldset>
            <div class="other__row">
              <button type="button" class="btn btn--primary btn--sm" :disabled="checking" @click="addOther">{{ t("asrSet.otherAdd") }}</button>
              <button type="button" class="btn btn--quiet btn--sm" @click="(found = null), (otherOpen = false)">{{ t("common.cancel") }}</button>
            </div>
          </div>
        </div>
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
      <div class="opt opt--stack terms">
        <span class="opt__label">
          {{ t("asrSet.vocab") }}
          <small>{{ t("asrSet.vocabHint") }}</small>
        </span>
        <div class="t-head" aria-hidden="true">
          <span>{{ t("asrSet.termFrom") }}</span>
          <span></span>
          <span>{{ t("asrSet.termTo") }}</span>
        </div>
        <ul class="t-rows">
          <li v-for="(r, i) in terms" :key="r.key" class="t-row">
            <input v-model="r.from" class="input t-from" :dir="r.from ? 'auto' : undefined" :aria-label="t('asrSet.termFromN', { n: i + 1 })" :placeholder="t('asrSet.termFromPh')" />
            <span class="t-arrow" aria-hidden="true">{{ $i18n.locale === "ar" ? "←" : "→" }}</span>
            <input v-model="r.to" class="input" :dir="r.to ? 'auto' : undefined" :aria-label="t('asrSet.termToN', { n: i + 1 })" :placeholder="t('asrSet.termToPh')" />
            <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('asrSet.termRemove', { n: i + 1 })" @click="terms.splice(i, 1)"><PhX :size="15" /></button>
          </li>
        </ul>
        <div class="t-actions">
          <button type="button" class="btn btn--outline btn--sm" @click="addTerm"><PhPlus :size="15" />{{ t("asrSet.termAdd") }}</button>
          <button type="button" class="btn btn--primary btn--sm" :disabled="saving" @click="saveTerms">{{ t("common.save") }}</button>
        </div>
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
  cursor: default;
  display: grid;
  grid-template-columns: auto 1fr auto;
  grid-template-areas:
    "name tags acc"
    "meta meta del"
    "warn warn warn";
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
.uses {
  display: grid;
  gap: var(--s-3);
  margin-bottom: var(--s-4);
}
.use {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 240px);
  grid-template-areas:
    "label select"
    "label now";
  column-gap: var(--s-3);
  row-gap: 2px;
  align-items: center;
  padding-bottom: var(--s-3);
  border-bottom: 1px solid var(--line);
}
.use__label {
  grid-area: label;
  display: grid;
  gap: 2px;
  font-weight: 600;
}
.use__label small {
  font-weight: 400;
  font-size: var(--fs-xs);
  opacity: 0.8;
}
.use__select {
  grid-area: select;
  width: 100%;
}
.use__now {
  grid-area: now;
  font-size: var(--fs-xs);
  opacity: 0.75;
}
.small-note {
  font-size: var(--fs-xs);
}
.add-for {
  border: 0;
  padding: 0;
  margin: 4px 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-3);
  font-size: var(--fs-sm);
}
.add-for legend {
  margin-bottom: 4px;
}
.add-for label {
  display: inline-flex;
  gap: 6px;
  align-items: center;
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
.terms {
  display: grid;
  gap: var(--s-2);
}
.t-head,
.t-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20px minmax(0, 1fr) 34px;
  gap: var(--s-2);
  align-items: center;
}
.t-head {
  font-size: var(--fs-xs);
  color: var(--text-2);
}
.t-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.t-arrow {
  color: var(--text-3);
  text-align: center;
}
.t-actions {
  display: flex;
  gap: var(--s-2);
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
.m-unknown {
  font-size: var(--fs-xs);
  opacity: 0.7;
}
.other-open {
  justify-self: start;
  margin-top: 4px;
}
.other {
  margin-top: 4px;
  padding: var(--s-3);
  border-radius: var(--r-md);
  border: 1px dashed var(--line-strong, var(--line));
  display: grid;
  gap: var(--s-2);
}
.other__lead {
  font-size: var(--fs-sm);
  opacity: 0.85;
}
.other__row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-2);
}
.other__row .input {
  flex: 1;
  min-width: 0;
}
.found {
  display: grid;
  gap: 4px;
  padding: var(--s-3);
  border-radius: var(--r-md);
  background: var(--surface-2);
}
.found__name {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.found__meta {
  font-size: var(--fs-sm);
}
.found__warn {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  font-size: var(--fs-xs);
  opacity: 0.85;
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
  .use {
    grid-template-columns: 1fr;
    grid-template-areas:
      "label"
      "select"
      "now";
  }
  .model {
    grid-template-columns: 1fr auto;
    grid-template-areas:
      "name acc"
      "tags tags"
      "meta del"
      "warn warn";
  }
  .sel {
    min-width: 0;
    width: 100%;
  }
}
</style>
