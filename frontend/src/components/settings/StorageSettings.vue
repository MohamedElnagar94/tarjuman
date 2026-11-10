<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { api, errorCode } from "@/api/client";
import { toast } from "@/composables/toast";
import { formatSize } from "@/lib/time";

type Usage = Record<string, { bytes: number; files: number }>;

const { t } = useI18n();
const units = computed(() => ({ kb: t("units.kb"), mb: t("units.mb"), gb: t("units.gb") }));
const usage = ref<Usage | null>(null);
const limit = ref(0);
const remote = ref(false);
const confirm = ref("");
const busy = ref("");

// Order and what can be cleared here. Videos and finished files are managed in "My files".
const ROWS = [
  { id: "voices", clear: true },
  { id: "translations", clear: true },
  { id: "tmp", clear: true },
  { id: "dubbed", clear: false },
  { id: "media", clear: false },
  { id: "subtitles", clear: false },
  { id: "models", clear: false },
] as const;

const total = computed(() => Object.values(usage.value || {}).reduce((n, u) => n + u.bytes, 0));

async function load() {
  try {
    const r = await api.storage();
    usage.value = r.usage;
    limit.value = r.voiceLimit;
  } catch {
    remote.value = true;
  }
}

async function clear(what: string) {
  if (confirm.value !== what) {
    confirm.value = what;
    return;
  }
  confirm.value = "";
  busy.value = what;
  try {
    usage.value = (await api.clearStorage(what)).usage;
    toast(t("storage.cleared"));
  } catch (e) {
    toast(t("errors." + errorCode(e), t("errors.UNKNOWN")), { tone: "danger" });
  } finally {
    busy.value = "";
  }
}

onMounted(load);
</script>

<template>
  <div>
    <p class="panel__lead">{{ t("storage.lead") }}</p>
    <p v-if="remote" class="muted">{{ t("phone.remote") }}</p>
    <table v-else-if="usage" class="table">
      <tbody>
        <tr v-for="r in ROWS" :key="r.id">
          <th scope="row">
            {{ t("storage." + r.id) }}
            <small>{{ t("storage." + r.id + "Hint", { limit: formatSize(limit, units) }) }}</small>
          </th>
          <td class="mono size">{{ formatSize(usage[r.id]?.bytes || 0, units) }}</td>
          <td class="act">
            <button
              v-if="r.clear"
              type="button"
              class="btn btn--sm"
              :class="confirm === r.id ? 'btn--primary' : 'btn--quiet'"
              :disabled="busy === r.id || !(usage[r.id]?.bytes)"
              @click="clear(r.id)"
            >
              {{ confirm === r.id ? t("storage.confirm") : t("storage.clear") }}
            </button>
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <th scope="row">{{ t("storage.total") }}</th>
          <td class="mono size">{{ formatSize(total, units) }}</td>
          <td />
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<style scoped>
.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: var(--s-3);
}
.table th,
.table td {
  padding: var(--s-2) 0;
  border-bottom: 1px solid var(--line, rgba(127, 127, 127, 0.18));
  text-align: start;
  vertical-align: middle;
}
.table th {
  font-weight: 600;
}
.table th small {
  display: block;
  font-weight: 400;
  color: var(--text-2);
  font-size: var(--fs-sm);
  margin-top: 2px;
}
.size {
  white-space: nowrap;
  padding-inline: var(--s-4) !important;
}
.act {
  text-align: end !important;
  width: 1%;
  white-space: nowrap;
}
tfoot th,
tfoot td {
  border-bottom: 0;
}
</style>
