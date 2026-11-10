<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import QRCode from "qrcode";
import { api, ApiError } from "@/api/client";
import { toast } from "@/composables/toast";

const { t } = useI18n();
const link = ref("");
const qr = ref("");
const state = ref<"loading" | "ready" | "nolan" | "remote" | "error">("loading");
const confirming = ref(false);

async function show(links: string[]) {
  link.value = links[0] || "";
  if (!link.value) {
    state.value = "nolan";
    return;
  }
  qr.value = await QRCode.toString(link.value, { type: "svg", margin: 1, errorCorrectionLevel: "M" });
  state.value = "ready";
}

async function load() {
  try {
    await show((await api.pairing()).links);
  } catch (e) {
    // Pairing is handed out from the computer only; on a paired phone this section just says so.
    state.value = e instanceof ApiError && e.code === "LOCAL_ONLY" ? "remote" : "error";
  }
}

async function reset() {
  if (!confirming.value) {
    confirming.value = true;
    return;
  }
  confirming.value = false;
  try {
    await show((await api.resetPairing()).links);
    toast(t("phone.resetDone"));
  } catch {
    toast(t("errors.UNKNOWN"), { tone: "danger" });
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(link.value);
    toast(t("common.copied"));
  } catch {}
}

onMounted(load);
</script>

<template>
  <div class="phone">
    <p class="panel__lead">{{ t("phone.lead") }}</p>
    <p v-if="state === 'remote'" class="muted">{{ t("phone.remote") }}</p>
    <p v-else-if="state === 'nolan'" class="muted">{{ t("phone.noLan") }}</p>
    <p v-else-if="state === 'error'" class="muted">{{ t("errors.UNKNOWN") }}</p>
    <div v-else-if="state === 'ready'" class="pair">
      <!-- The SVG comes from the QR library and holds only the pairing link. -->
      <div class="qr" role="img" :aria-label="t('phone.qrLabel')" v-html="qr" />
      <ol class="steps">
        <li>{{ t("phone.step1") }}</li>
        <li>{{ t("phone.step2") }}</li>
        <li>{{ t("phone.step3") }}</li>
      </ol>
    </div>
    <div v-if="state === 'ready'" class="link">
      <code dir="ltr" class="mono">{{ link }}</code>
      <button type="button" class="btn btn--outline btn--sm" @click="copy">{{ t("phone.copy") }}</button>
    </div>
    <p v-if="state === 'ready'" class="muted small">{{ t("phone.firewall") }}</p>
    <div v-if="state === 'ready'" class="actions">
      <button type="button" class="btn btn--sm" :class="confirming ? 'btn--primary' : 'btn--quiet'" @click="reset">
        {{ confirming ? t("phone.resetConfirm") : t("phone.reset") }}
      </button>
      <span class="muted small">{{ t("phone.resetHint") }}</span>
    </div>
  </div>
</template>

<style scoped>
.pair {
  display: flex;
  gap: var(--s-5);
  align-items: center;
  flex-wrap: wrap;
  margin-top: var(--s-3);
}
.qr {
  width: 176px;
  height: 176px;
  padding: 10px;
  border-radius: var(--r-md);
  background: #fff; /* QR codes must stay dark on light to scan, in both themes */
  flex: none;
}
.qr :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}
.steps {
  margin: 0;
  padding-inline-start: 1.2em;
  line-height: 1.9;
}
.link {
  display: flex;
  gap: var(--s-2);
  align-items: center;
  flex-wrap: wrap;
  margin-top: var(--s-4);
}
.link code {
  padding: 6px 10px;
  border-radius: var(--r-sm);
  background: var(--surface-2, rgba(127, 127, 127, 0.12));
  font-size: var(--fs-sm);
  word-break: break-all;
}
.actions {
  display: flex;
  gap: var(--s-3);
  align-items: center;
  flex-wrap: wrap;
  margin-top: var(--s-4);
}
.small {
  font-size: var(--fs-sm);
}
</style>
