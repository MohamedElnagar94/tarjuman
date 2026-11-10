<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import QRCode from "qrcode";
import { PhDeviceMobile, PhPencilSimple, PhX } from "@phosphor-icons/vue";
import { api, ApiError, type PairedDevice, type PairingState } from "@/api/client";
import { toast } from "@/composables/toast";

const { t, locale } = useI18n();
const link = ref("");
const qr = ref("");
const devices = ref<PairedDevice[]>([]);
const state = ref<"loading" | "ready" | "nolan" | "remote" | "error">("loading");
const confirming = ref(""); // "all", "code" or a device id waiting for a second tap
const editing = ref("");
const newName = ref("");
let timer: number | undefined;

async function apply(s: PairingState) {
  devices.value = s.devices;
  if (s.links[0] !== link.value) {
    link.value = s.links[0] || "";
    qr.value = link.value ? await QRCode.toString(link.value, { type: "svg", margin: 1, errorCorrectionLevel: "M" }) : "";
  }
  state.value = link.value ? "ready" : "nolan";
}

async function load() {
  try {
    await apply(await api.pairing());
  } catch (e) {
    // Pairing is managed from the computer only; on a paired phone this section just says so.
    state.value = e instanceof ApiError && e.code === "LOCAL_ONLY" ? "remote" : "error";
    clearInterval(timer);
  }
}

/** A second tap confirms; the first only arms the button. */
function armed(what: string): boolean {
  if (confirming.value === what) {
    confirming.value = "";
    return true;
  }
  confirming.value = what;
  return false;
}

async function run(p: Promise<PairingState>, done: string) {
  try {
    await apply(await p);
    toast(t(done));
  } catch {
    toast(t("errors.UNKNOWN"), { tone: "danger" });
  }
}

const remove = (d: PairedDevice) => armed(d.id) && run(api.pairingDevice(d.id, "remove"), "phone.removed");
const newCode = () => armed("code") && run(api.resetPairing(), "phone.codeDone");
const unpairAll = () => armed("all") && run(api.unpairAll(), "phone.resetDone");

function startRename(d: PairedDevice) {
  editing.value = d.id;
  newName.value = d.name;
}
async function saveName(d: PairedDevice) {
  editing.value = "";
  if (newName.value.trim() && newName.value !== d.name) await run(api.pairingDevice(d.id, "rename", newName.value), "phone.renamed");
}

// The app asks the server every few seconds while open, so two minutes of silence means it is closed.
const online = (d: PairedDevice) => Date.now() - d.lastSeen < 120_000;

const rtf = computed(() => new Intl.RelativeTimeFormat(locale.value, { numeric: "auto" }));
function ago(ms: number): string {
  const s = Math.round((ms - Date.now()) / 1000);
  if (s > -60) return t("phone.now");
  if (s > -3600) return rtf.value.format(Math.round(s / 60), "minute");
  if (s > -86400) return rtf.value.format(Math.round(s / 3600), "hour");
  return rtf.value.format(Math.round(s / 86400), "day");
}

async function copy() {
  try {
    await navigator.clipboard.writeText(link.value);
    toast(t("common.copied"));
  } catch {}
}

onMounted(() => {
  void load();
  // A phone that just scanned the code shows up here by itself.
  timer = window.setInterval(load, 4000);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<template>
  <div class="phone">
    <p class="panel__lead">{{ t("phone.lead") }}</p>
    <p v-if="state === 'remote'" class="muted">{{ t("phone.remote") }}</p>
    <p v-else-if="state === 'nolan'" class="muted">{{ t("phone.noLan") }}</p>
    <p v-else-if="state === 'error'" class="muted">{{ t("errors.UNKNOWN") }}</p>

    <template v-if="state === 'ready' || state === 'nolan'">
      <div v-if="state === 'ready'" class="pair">
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
        <button type="button" class="btn btn--sm" :class="confirming === 'code' ? 'btn--primary' : 'btn--quiet'" @click="newCode">
          {{ confirming === "code" ? t("phone.codeConfirm") : t("phone.newCode") }}
        </button>
      </div>
      <p v-if="state === 'ready'" class="muted small">{{ t("phone.codeHint") }} {{ t("phone.firewall") }}</p>

      <h3 class="sub">{{ t("phone.devices", { n: devices.length }) }}</h3>
      <p v-if="!devices.length" class="muted">{{ t("phone.noDevices") }}</p>
      <ul v-else class="devices">
        <li v-for="d in devices" :key="d.id" class="device" :class="{ 'device--online': online(d) }">
          <span class="device__tile" aria-hidden="true">
            <PhDeviceMobile :size="22" weight="duotone" />
            <span class="device__dot" />
          </span>
          <div class="device__info">
            <form v-if="editing === d.id" class="rename" @submit.prevent="saveName(d)">
              <input v-model="newName" class="input" maxlength="60" :aria-label="t('phone.nameLabel')" @keydown.esc="editing = ''" />
              <button type="submit" class="btn btn--primary btn--sm">{{ t("common.save") }}</button>
              <button type="button" class="btn btn--quiet btn--sm" @click="editing = ''">{{ t("common.cancel") }}</button>
            </form>
            <!-- bdi keeps a Latin name in order while the line itself follows the page side -->
            <strong v-else class="device__name"><bdi>{{ d.name }}</bdi></strong>
            <div class="device__meta">
              <span class="device__status" :title="t('phone.pairedAt', { when: new Date(d.pairedAt).toLocaleString(locale) })">
                {{ online(d) ? t("phone.online") : t("phone.lastSeen", { when: ago(d.lastSeen) }) }}
              </span>
              <span v-if="d.lastIp" class="device__ip mono" dir="ltr">{{ d.lastIp }}</span>
            </div>
          </div>
          <div v-if="editing !== d.id" class="device__actions">
            <button type="button" class="btn btn--quiet btn--icon btn--sm" :title="t('phone.rename')" :aria-label="t('phone.rename')" @click="startRename(d)">
              <PhPencilSimple :size="17" />
            </button>
            <button
              type="button"
              class="btn btn--sm device__remove"
              :class="confirming === d.id ? 'btn--danger' : 'btn--quiet'"
              @click="remove(d)"
              @blur="confirming === d.id && (confirming = '')"
            >
              <PhX v-if="confirming !== d.id" :size="15" />
              {{ confirming === d.id ? t("phone.removeConfirm") : t("phone.remove") }}
            </button>
          </div>
        </li>
      </ul>
      <div v-if="devices.length > 1" class="actions">
        <button type="button" class="btn btn--sm" :class="confirming === 'all' ? 'btn--primary' : 'btn--quiet'" @click="unpairAll">
          {{ confirming === "all" ? t("phone.resetConfirm") : t("phone.reset") }}
        </button>
      </div>
    </template>
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
.sub {
  font-size: var(--fs-md, 1rem);
  margin: var(--s-5) 0 var(--s-2);
}
.devices {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--s-2);
}
.device {
  display: flex;
  align-items: center;
  gap: var(--s-4);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r-lg);
  border: 1px solid var(--line);
  background: var(--surface-2);
  transition: border-color var(--dur) var(--ease);
}
.device:hover {
  border-color: var(--line-2);
}
.device__tile {
  position: relative;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: var(--r-md);
  background: var(--accent-soft);
  color: var(--accent);
}
/* Grey when the phone is away, green while it has Tarjuman open */
.device__dot {
  position: absolute;
  inset-block-end: -3px;
  inset-inline-end: -3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-3);
  border: 2px solid var(--surface-2);
}
.device--online .device__dot {
  background: var(--ok);
}
.device__info {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: var(--s-1);
}
.device__name {
  font-weight: 600;
  font-size: var(--fs-md);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.device__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--s-2);
  font-size: var(--fs-sm);
  color: var(--text-2);
}
.device--online .device__status {
  color: var(--ok);
}
.device__ip {
  padding: 1px 8px;
  border-radius: var(--r-pill);
  background: var(--surface-3);
  color: var(--text-2);
  font-size: var(--fs-xs);
}
.device__actions {
  display: flex;
  align-items: center;
  gap: var(--s-1);
  flex: none;
}
.device__remove:not(.btn--danger):hover {
  color: var(--danger);
  background: var(--danger-soft);
}
@media (max-width: 520px) {
  .device {
    flex-wrap: wrap;
  }
  .device__actions {
    width: 100%;
    justify-content: flex-end;
    border-top: 1px solid var(--line);
    padding-top: var(--s-2);
  }
}
.rename {
  display: flex;
  gap: var(--s-2);
}
.rename .input {
  flex: 1;
  min-width: 0;
}
.actions {
  margin-top: var(--s-3);
}
.small {
  font-size: var(--fs-sm);
}
</style>
