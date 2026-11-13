<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useI18n } from "vue-i18n";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api, errorCode } from "@/api/client";
import { toast } from "@/composables/toast";
import { useUpdates } from "@/composables/updates";
import { markdownToHtml } from "@/lib/markdown";

const { t, locale } = useI18n();
const { state, refresh } = useUpdates();
const checking = ref(false);
const confirmJobs = ref(false);
let timer: number | undefined;

const busy = computed(() => ["downloading", "verifying", "starting"].includes(state.value?.phase || ""));
const date = (iso: string) => (iso ? new Date(iso).toLocaleDateString(locale.value, { dateStyle: "medium" }) : "");

async function check() {
  checking.value = true;
  await refresh(true);
  checking.value = false;
  if (state.value?.error) toast(t("updates.checkFailed"), { tone: "danger" });
}

function follow() {
  // While the download runs, read its progress from this computer's own server (not from GitHub).
  clearInterval(timer);
  timer = window.setInterval(async () => {
    await refresh();
    if (!busy.value) clearInterval(timer);
  }, 800);
}

async function install(force = false) {
  try {
    state.value = { ...(await api.installUpdate(force)), ok: true };
    confirmJobs.value = false;
    follow();
  } catch (e) {
    if (errorCode(e) === "JOBS_RUNNING") confirmJobs.value = true;
    else toast(t("errors." + errorCode(e), t("errors.UNKNOWN")), { tone: "danger" });
  }
}

async function setOption(key: "checkUpdates" | "autoUpdate", on: boolean) {
  await api.setDesktop({ [key]: on });
  await refresh();
}

onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <div>
    <p class="panel__lead">{{ t("updates.lead") }}</p>
    <template v-if="state">
      <div class="status">
        <div>
          <strong>{{ t("updates.current", { v: state.current }) }}</strong>
          <small class="muted">
            {{ state.available ? t("updates.newer", { v: state.latest }) : state.checkedAt ? t("updates.upToDate") : t("updates.never") }}
          </small>
        </div>
        <button type="button" class="btn btn--outline btn--sm" :disabled="checking || busy" @click="check">
          {{ checking ? t("updates.checking") : t("updates.check") }}
        </button>
      </div>

      <div v-if="state.available" class="card">
        <div v-for="r in state.releases" :key="r.version" class="rel">
          <h3 class="rel__head">
            <span>{{ t("updates.version", { v: r.version }) }}</span>
            <small class="muted">{{ date(r.date) }}</small>
          </h3>
          <!-- Escaped by markdownToHtml: the notes can't add markup of their own. -->
          <div v-if="r.notes" class="notes" dir="ltr" v-html="markdownToHtml(r.notes)" />
          <p v-else class="muted">{{ t("updates.noNotes") }}</p>
        </div>

        <div class="actions">
          <template v-if="state.canInstall">
            <template v-if="confirmJobs">
              <span class="warn">{{ t("updates.jobsRunning") }}</span>
              <button type="button" class="btn btn--primary btn--sm" @click="install(true)">{{ t("updates.installAnyway") }}</button>
              <button type="button" class="btn btn--quiet btn--sm" @click="confirmJobs = false">{{ t("common.cancel") }}</button>
            </template>
            <button v-else type="button" class="btn btn--primary" :disabled="busy" @click="install()">
              {{ busy ? t("updates.phase." + state.phase, { p: state.progress }) : t("updates.install", { v: state.latest }) }}
            </button>
            <small class="muted">{{ t("updates.installHint") }}</small>
          </template>
          <template v-else>
            <a class="btn btn--primary" :href="state.releases[0]?.page" target="_blank" rel="noopener">{{ t("updates.openPage") }}</a>
            <small class="muted">{{ state.installed ? t("updates.noChecksum") : t("updates.fromSource") }}</small>
          </template>
        </div>
        <p v-if="state.phase === 'error'" class="warn">{{ t("updates.failed", { m: state.message }) }}</p>
      </div>

      <div class="opt">
        <label class="opt__label" for="up-check">{{ t("updates.checkAuto") }}<small>{{ t("updates.checkAutoHint") }}</small></label>
        <ToggleSwitch id="up-check" :model-value="state.settings.checkUpdates" @update:model-value="setOption('checkUpdates', $event)" />
      </div>
      <div class="opt">
        <label class="opt__label" for="up-auto">{{ t("updates.auto") }}<small>{{ t("updates.autoHint") }}</small></label>
        <ToggleSwitch
          id="up-auto"
          :model-value="state.settings.autoUpdate"
          :disabled="!state.installed || !state.settings.checkUpdates"
          @update:model-value="setOption('autoUpdate', $event)"
        />
      </div>
    </template>
    <p v-else class="muted">{{ t("phone.remote") }}</p>
  </div>
</template>

<style scoped>
.status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  flex-wrap: wrap;
  margin: var(--s-3) 0;
}
.status > div {
  display: grid;
  gap: 2px;
}
.card {
  border: 1px solid var(--accent-line);
  background: var(--accent-soft);
  border-radius: var(--r-lg);
  padding: var(--s-3) var(--s-4);
  margin-bottom: var(--s-4);
}
.rel + .rel {
  border-top: 1px solid var(--line);
  margin-top: var(--s-3);
  padding-top: var(--s-3);
}
.rel__head {
  display: flex;
  align-items: baseline;
  gap: var(--s-3);
  font-size: var(--fs-md);
  margin: 0 0 var(--s-2);
}
.notes {
  font-size: var(--fs-sm);
  line-height: 1.7;
  max-height: 320px;
  overflow: auto;
  text-align: start;
}
.notes :deep(h4),
.notes :deep(h5),
.notes :deep(h6) {
  font-size: var(--fs-sm);
  margin: var(--s-3) 0 var(--s-1);
}
.notes :deep(ul) {
  margin: 0;
  padding-inline-start: 1.2em;
}
.notes :deep(hr) {
  border: 0;
  border-top: 1px solid var(--line);
  margin: var(--s-3) 0;
}
.notes :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.92em;
}
.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--s-3);
  margin-top: var(--s-4);
}
.warn {
  color: var(--danger);
  font-size: var(--fs-sm);
}
</style>
