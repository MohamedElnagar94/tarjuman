<script setup lang="ts">
/* Offline translation (backend translate/local.py): one model per language pair, downloaded from the
   University of Helsinki and prepared on this computer. Downloads take minutes, so the list refreshes
   by itself while one runs. */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhCheckCircle, PhDownloadSimple, PhMagnifyingGlass, PhTrash, PhWarningCircle } from "@phosphor-icons/vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import { api, errorCode } from "@/api/client";
import type { MtState } from "@/api/types";
import { errText } from "@/i18n";
import { langName } from "@/lib/langs";
import { toast } from "@/composables/toast";

const { t, locale } = useI18n();
const st = ref<MtState | null>(null);
const q = ref("");
let timer: number | undefined;

async function refresh() {
  try {
    st.value = await api.mt();
  } catch {
    /* the page says nothing new; it tries again on the next tick while a download runs */
  }
  schedule();
}
function schedule() {
  window.clearTimeout(timer);
  const working = Object.values(st.value?.installs || {}).some((x) => x.status === "working");
  if (working) timer = window.setTimeout(refresh, 1500);
}
onMounted(refresh);
onBeforeUnmount(() => window.clearTimeout(timer));

async function run(fn: () => Promise<MtState>) {
  try {
    st.value = await fn();
  } catch (e) {
    toast(errText(errorCode(e), (e as Error).message), { tone: "danger" });
  }
  schedule();
}
const install = (pair: string) => run(() => api.installMt(pair));
const remove = (pair: string) => run(() => api.deleteMt(pair));
const setPrefer = (v: "online" | "offline") => run(() => api.setMt(v));

const preferOptions = computed(() => [
  { value: "online" as const, label: t("mt.online") },
  { value: "offline" as const, label: t("mt.offline") },
]);

const size = (n: number) => (n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : `${Math.round(n / 1e6)} MB`);

type Row = { pair: string; lang: string; name: string };
const rows = (dir: "to" | "from") =>
  computed<Row[]>(() => {
    const avail = st.value?.available || [];
    const out = avail
      .filter((p) => (dir === "to" ? p.startsWith("en-") : p.endsWith("-en")))
      .map((pair) => {
        const lang = dir === "to" ? pair.slice(3) : pair.slice(0, -3);
        return { pair, lang, name: langName(lang, locale.value) };
      });
    const needle = q.value.trim().toLowerCase();
    return out
      .filter((r) => !needle || r.name.toLowerCase().includes(needle) || r.lang.includes(needle))
      .sort((a, b) => Number(isIn(b.pair)) - Number(isIn(a.pair)) || a.name.localeCompare(b.name, locale.value));
  });
const toRows = rows("to");
const fromRows = rows("from");
const isIn = (pair: string) => !!st.value?.installed.includes(pair);
const job = (pair: string) => st.value?.installs?.[pair];
</script>

<template>
  <div class="mt">
    <p class="panel__lead">{{ t("mt.lead") }}</p>
    <p class="note"><PhWarningCircle :size="17" aria-hidden="true" />{{ t("mt.honest") }}</p>

    <template v-if="st">
      <div class="opt">
        <span class="opt__label">{{ t("mt.prefer") }}<small>{{ st.prefer === "offline" ? t("mt.offlineHint") : t("mt.onlineHint") }}</small></span>
        <SegmentedControl :model-value="st.prefer" :options="preferOptions" :label="t('mt.prefer')" size="sm" @update:model-value="setPrefer" />
      </div>

      <label class="find">
        <PhMagnifyingGlass :size="16" aria-hidden="true" />
        <span class="sr-only">{{ t("mt.search") }}</span>
        <input v-model="q" type="search" class="input" :placeholder="t('mt.search')" />
      </label>
      <p class="muted small">{{ t("mt.size") }}</p>

      <template v-for="group in [{ key: 'to', title: t('mt.toLangs'), list: toRows }, { key: 'from', title: t('mt.fromLangs'), list: fromRows }]" :key="group.key">
        <h3 class="group">{{ group.title }}</h3>
        <p v-if="group.key === 'from'" class="muted small">{{ t("mt.fromHint") }}</p>
        <ul class="langs">
          <li v-for="r in group.list" :key="r.pair" class="lang" :class="{ on: isIn(r.pair) }">
            <span class="name">{{ r.name }}</span>
            <template v-if="isIn(r.pair)">
              <span class="state ok"><PhCheckCircle :size="15" weight="fill" />{{ t("mt.installed", { size: size(st.bytes[r.pair] || 0) }) }}</span>
              <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('mt.remove') + ' — ' + r.name" :title="t('mt.remove')" @click="remove(r.pair)">
                <PhTrash :size="15" />
              </button>
            </template>
            <template v-else-if="job(r.pair)?.status === 'working'">
              <span class="state">{{ job(r.pair)!.phase === "convert" ? t("mt.converting") : t("mt.downloading", { pct: job(r.pair)!.progress }) }}</span>
              <progress :value="job(r.pair)!.progress" max="100"></progress>
            </template>
            <template v-else>
              <span v-if="job(r.pair)?.status === 'error'" class="state err">{{ t("mt.failed") }}</span>
              <button type="button" class="btn btn--outline btn--sm" @click="install(r.pair)">
                <PhDownloadSimple :size="15" />{{ job(r.pair)?.status === "error" ? t("mt.retry") : t("mt.get") }}
              </button>
            </template>
          </li>
        </ul>
      </template>
      <p class="muted small">{{ t("mt.none") }}</p>
    </template>
  </div>
</template>

<style scoped>
.mt {
  display: grid;
  gap: var(--s-3);
}
.note {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: var(--s-3);
  border-radius: var(--r-md);
  background: var(--surface-2);
  color: var(--text-2);
  font-size: var(--fs-sm);
}
.note svg {
  flex: none;
  margin-top: 3px;
  color: var(--accent-ink);
}
.find {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 320px;
  color: var(--text-3);
}
.find .input {
  flex: 1;
}
.group {
  margin-top: var(--s-3);
  font-size: var(--fs-md);
}
.langs {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
  gap: 8px;
}
.lang {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--surface-1);
}
.lang.on {
  border-color: var(--accent-line);
}
.name {
  flex: 1;
  min-width: 0;
  font-weight: 600;
}
.state {
  font-size: 12px;
  color: var(--text-2);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.state.ok {
  color: var(--ok, #3fb67b);
}
.state.err {
  color: var(--danger, #e0605e);
}
progress {
  width: 70px;
}
.small {
  font-size: var(--fs-sm);
}
</style>
