<script setup lang="ts">
/* Voice packs (backend engines/packs.py): the speaker's own voice (XTTS) and Arabic dialect voices
   (Habibi). Each needs PyTorch and a few GB, so it is installed only on request, in its own folder.
   Habibi is shown when the computer has a capable NVIDIA card; elsewhere it is behind "show anyway". */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhCheckCircle, PhDownloadSimple, PhTrash, PhWarningCircle } from "@phosphor-icons/vue";
import { api, errorCode } from "@/api/client";
import type { PacksState, VoicePack } from "@/api/types";
import { errText } from "@/i18n";
import { usePacks } from "@/composables/packs";
import { toast } from "@/composables/toast";

const { t } = useI18n();
const { packs } = usePacks();
const accepted = ref(false);
const showHeavy = ref(false);
let timer: number | undefined;

const working = computed(() => !!packs.value?.packs.some((p) => p.status === "working"));
function schedule() {
  window.clearTimeout(timer);
  if (working.value) timer = window.setTimeout(load, 3000);
}
async function load() {
  try {
    packs.value = await api.packs();
  } catch {
    /* tried again on the next tick while something installs */
  }
  schedule();
}
onMounted(load);
onBeforeUnmount(() => window.clearTimeout(timer));

async function run(fn: () => Promise<PacksState>) {
  try {
    packs.value = await fn();
  } catch (e) {
    toast(errText(errorCode(e), (e as Error).message), { tone: "danger" });
  }
  schedule();
}
const install = (p: VoicePack) => run(() => api.installPack(p.name, p.name === "xtts" ? accepted.value : false));
const remove = (p: VoicePack) => run(() => api.deletePack(p.name));

const visible = computed(() => (packs.value?.packs || []).filter((p) => !p.needsGpu || packs.value?.strongGpu || showHeavy.value || p.installed));
const hiddenHeavy = computed(() => (packs.value?.packs || []).some((p) => p.needsGpu && !packs.value?.strongGpu && !p.installed));
const phase = (p: VoicePack) => t("packs.phase." + (p.phase || "venv"));
</script>

<template>
  <div class="packs">
    <p class="panel__lead">{{ t("packs.lead") }}</p>

    <article v-for="p in visible" :key="p.name" class="pack" :class="{ on: p.installed }">
      <header>
        <h3>{{ t("packs." + p.name + ".title") }}</h3>
        <span class="size">{{ t("packs.size", { gb: p.sizeGb }) }}</span>
      </header>
      <p>{{ t("packs." + p.name + ".body") }}</p>
      <p class="muted small">{{ t("packs." + p.name + ".speed") }}</p>
      <p v-if="p.needsGpu && !packs?.strongGpu" class="warn"><PhWarningCircle :size="16" />{{ t("packs.noGpu") }}</p>

      <div v-if="p.installed" class="row">
        <span class="ok"><PhCheckCircle :size="16" weight="fill" />{{ t("packs.installed") }}</span>
        <button type="button" class="btn btn--quiet btn--sm" @click="remove(p)"><PhTrash :size="15" />{{ t("packs.remove") }}</button>
      </div>
      <div v-else-if="p.status === 'working'" class="row">
        <span class="busy">{{ phase(p) }}</span>
        <small class="log mono" dir="ltr">{{ p.log }}</small>
      </div>
      <div v-else class="row col">
        <label v-if="p.licence === 'CPML'" class="licence">
          <input v-model="accepted" type="checkbox" />
          <span>{{ t("packs.xtts.licence") }} <a href="https://coqui.ai/cpml" target="_blank" rel="noopener">CPML</a></span>
        </label>
        <p v-if="p.status === 'error'" class="err">{{ t("packs.failed") }}</p>
        <button type="button" class="btn btn--primary btn--sm" :disabled="p.licence === 'CPML' && !accepted" @click="install(p)">
          <PhDownloadSimple :size="15" />{{ p.status === "error" ? t("packs.retry") : t("packs.install") }}
        </button>
      </div>
    </article>

    <button v-if="hiddenHeavy && !showHeavy" type="button" class="btn btn--quiet btn--sm more" @click="showHeavy = true">{{ t("packs.showHeavy") }}</button>
    <p class="muted small">{{ t("packs.where") }}</p>
  </div>
</template>

<style scoped>
.packs {
  display: grid;
  gap: var(--s-3);
}
.pack {
  display: grid;
  gap: 6px;
  padding: var(--s-4);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  background: var(--surface-1);
}
.pack.on {
  border-color: var(--accent-line);
}
.pack header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s-3);
}
.pack h3 {
  font-size: var(--fs-md);
}
.size {
  color: var(--text-3);
  font-size: 12px;
  flex: none;
}
.row {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  flex-wrap: wrap;
  margin-top: 4px;
}
.row.col {
  flex-direction: column;
  align-items: flex-start;
}
.ok {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--ok, #3fb67b);
  font-weight: 600;
}
.busy {
  font-weight: 600;
}
.log {
  color: var(--text-3);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.licence {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: var(--fs-sm);
}
.warn {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  color: var(--accent-ink);
  font-size: var(--fs-sm);
}
.err {
  color: var(--danger, #e0605e);
  font-size: var(--fs-sm);
}
.small {
  font-size: var(--fs-sm);
}
.more {
  justify-self: start;
}
</style>
