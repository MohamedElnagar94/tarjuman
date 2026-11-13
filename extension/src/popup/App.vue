<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { t } from "@/shared/i18n";
import { send } from "@/shared/messages";
import { TARGET_LANGS } from "@/shared/settings";
import { useExtension } from "@/ui/useExtension";
import { startError, shortcutText } from "@/ui/errors";
import ToggleSwitch from "@/ui/ToggleSwitch.vue";
import SegmentedControl from "@/ui/SegmentedControl.vue";
import SizeStepper from "@/ui/SizeStepper.vue";
import SubtitlePreview from "@/ui/SubtitlePreview.vue";
import VoicePicker from "@/ui/VoicePicker.vue";

const { settings, status, loaded, voices, previewing, refresh, update, loadVoices, previewVoice } = useExtension();

const busy = ref(false);
const error = ref("");
const note = ref("");
const shortcut = ref("");
const retrying = ref(false);

const running = computed(() => !!status.value?.activeHere);
const runMode = computed(() => (running.value ? status.value?.state.mode : null));
const tab = computed(() => status.value?.tab || null);
const online = computed(() => !!status.value?.health);
// The app answers but hasn't approved this extension yet (it trusts the first one that connects).
const notAllowed = computed(() => (status.value?.health as { extensionAllowed?: boolean } | null)?.extensionAllowed === false);
// Two separate versions: this extension's own (its manifest), and the desktop app's when it answers.
// Showing only the app's made it look like the extension's.
const extVersion = computed(() => status.value?.version || "");
const appVersion = computed(() => (online.value && (status.value?.health?.version as string)) || "");
// The protocol this extension speaks (the app reports its own as `api` since 3.1). An older app
// still works for the basics; the notice asks to update it.
const MIN_API = 1;
const appTooOld = computed(() => online.value && Number((status.value?.health as { api?: number } | null)?.api || 0) < MIN_API);
const RELEASES = "https://github.com/MohamedElnagar94/tarjuman/releases/latest";
const blocked = computed(() => !!tab.value?.protected);

const modeLabel = computed(() => {
  if (!tab.value) return "";
  if (blocked.value) return t("modeProtectedShort");
  if (tab.value.youtube) return t("modeYouTube");
  if (runMode.value === "captions") return t("modeCaptions");
  if (runMode.value === "live") return t("modeLive");
  return t("modeSite");
});

const modeHint = computed(() => {
  if (!tab.value) return "";
  if (blocked.value) return t("hintProtected");
  if (tab.value.youtube) return t("hintYouTube");
  if (runMode.value === "captions") return t("hintCaptions");
  if (runMode.value === "live") return t("hintLive");
  return t("hintSite");
});

/** Running on a site the user hasn't granted: it works now but stops after a reload. */
const sessionOnly = computed(() => running.value && tab.value && !tab.value.youtube && !tab.value.siteGranted);

const positions = computed(() => [
  { value: "bottom", label: t("posBottom") },
  { value: "top", label: t("posTop") },
]);

async function doStart() {
  const r = await send("start", { tabId: tab.value?.id });
  if (!r.ok) error.value = startError(r);
  await refresh();
}

async function toggle() {
  if (busy.value) return;
  error.value = "";
  note.value = "";
  busy.value = true;
  try {
    if (running.value) {
      await send("stop");
      await refresh();
      return;
    }
    const tb = tab.value;
    // First time outside YouTube: ask for this site only (least privilege). activeTab already
    // covers this session, so a "no" still translates; a "yes" keeps it working across reloads.
    if (tb && !tb.youtube && tb.origin && !tb.siteGranted && !declined(tb.origin)) {
      void send("pending-start", { tabId: tb.id });
      let granted = false;
      try {
        // The player often lives in an iframe from another site; it needs the same permission.
        granted = await chrome.permissions.request({ origins: [tb.origin, ...(tb.frameOrigins || [])] });
      } catch {}
      if (!granted) remember(tb.origin);
    }
    await doStart();
  } finally {
    busy.value = false;
  }
}

async function allowSite() {
  const tb = tab.value;
  if (!tb?.origin) return;
  try {
    if (await chrome.permissions.request({ origins: [tb.origin, ...(tb.frameOrigins || [])] })) {
      forget(tb.origin);
      await refresh();
    }
  } catch {}
}

// Remember a refusal so the prompt doesn't come back on every click.
function declined(origin: string) {
  try {
    return JSON.parse(localStorage.getItem("declined") || "[]").includes(origin);
  } catch {
    return false;
  }
}
function remember(origin: string) {
  try {
    const list: string[] = JSON.parse(localStorage.getItem("declined") || "[]");
    if (!list.includes(origin)) localStorage.setItem("declined", JSON.stringify([...list, origin].slice(-50)));
  } catch {}
}
function forget(origin: string) {
  try {
    const list: string[] = JSON.parse(localStorage.getItem("declined") || "[]");
    localStorage.setItem("declined", JSON.stringify(list.filter((o) => o !== origin)));
  } catch {}
}

async function changeLang(lang: string) {
  await update({ lang, voice: "" });
  await loadVoices();
}

async function preview() {
  note.value = "";
  if (!(await previewVoice())) note.value = t("errVoice");
}

async function retry() {
  retrying.value = true;
  await refresh();
  if (online.value) await loadVoices();
  retrying.value = false;
}

function openApp() {
  send("open-app");
  window.close();
}
function openOptions() {
  send("open-options");
  window.close();
}
function openWelcome() {
  send("open-welcome");
  window.close();
}

onMounted(async () => {
  shortcut.value = await shortcutText();
  await refresh();
  if (online.value) await loadVoices();
});
</script>

<template>
  <div class="popup">
    <header class="head">
      <img class="mark" src="/icons/icon.svg" alt="" width="34" height="34" />
      <div class="brand">
        <h1>{{ t("extShortName") }}</h1>
        <p>{{ t("taglineShort") }}</p>
      </div>
      <div class="conn" :class="{ ok: online, bad: loaded && !online }" role="status">
        <i aria-hidden="true"></i>
        <span>{{ !loaded ? t("connSearching") : online ? t("connOnline") : t("connOffline") }}</span>
      </div>
    </header>

    <main class="body">
      <!-- Loading -->
      <div v-if="!loaded" class="skeleton" aria-hidden="true">
        <div class="sk screen"></div>
        <div class="sk cta"></div>
        <div class="sk card"></div>
      </div>

      <!-- The local app isn't running -->
      <section v-else-if="!online" class="offline">
        <div class="glyph" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="4" width="20" height="13" rx="2.5" /><path d="M8 21h8M12 17v4" /><path d="m9.5 8.5 5 5M14.5 8.5l-5 5" />
          </svg>
        </div>
        <h2>{{ t("offlineTitle") }}</h2>
        <p>{{ t("offlineBody") }}</p>
        <div class="offline-actions">
          <button type="button" class="btn primary" @click="openWelcome">{{ t("btnHowToStart") }}</button>
          <button type="button" class="btn" :disabled="retrying" @click="retry">{{ retrying ? t("connSearching") : t("btnRetry") }}</button>
        </div>
        <p class="small">{{ t("offlineHint") }}</p>
      </section>

      <!-- The app runs but another extension was approved first -->
      <section v-else-if="notAllowed" class="offline">
        <h2>{{ t("notAllowedTitle") }}</h2>
        <p>{{ t("notAllowedBody") }}</p>
        <div class="offline-actions">
          <button type="button" class="btn" :disabled="retrying" @click="retry">{{ retrying ? t("connSearching") : t("btnRetry") }}</button>
        </div>
      </section>

      <!-- Controls -->
      <template v-else>
        <p v-if="appTooOld" class="note-old" role="note">
          {{ t("appTooOld") }}
          <a :href="RELEASES" target="_blank" rel="noopener">{{ t("appUpdateLink") }}</a>
        </p>
        <section class="stage">
          <SubtitlePreview :settings="settings" :active="running" :label="modeLabel" />
          <button
            type="button"
            class="cta"
            :class="{ stop: running, 'busy-state': busy }"
            :disabled="busy || blocked"
            :aria-pressed="running"
            @click="toggle"
          >
            <span v-if="busy" class="spin" aria-hidden="true"></span>
            <svg v-else-if="running" viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2.5" /></svg>
            <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5Z" /></svg>
            <span>{{ busy ? t("btnStarting") : running ? t("btnStop") : t("btnStart") }}</span>
          </button>
          <p class="hint">{{ modeHint }}</p>
          <p v-if="error" class="msg err" role="alert">{{ error }}</p>
          <p v-if="sessionOnly" class="msg info">
            {{ t("sessionOnly") }}
            <button type="button" class="link" @click="allowSite">{{ t("btnAllowSite") }}</button>
          </p>
        </section>

        <section class="card" :aria-label="t('secDub')">
          <div class="row">
            <label for="dub" class="lbl">
              <span>{{ t("lblDub") }}</span>
              <small>{{ t("lblDubHint") }}</small>
            </label>
            <ToggleSwitch id="dub" :model-value="settings.dub" @update:model-value="update({ dub: $event })" />
          </div>
          <div class="sub" :class="{ dim: !settings.dub }" :inert="!settings.dub || undefined">
            <div class="row">
              <label for="voice" class="lbl"><span>{{ t("lblVoice") }}</span></label>
              <VoicePicker id="voice" :model-value="settings.voice" :voices="voices" :previewing="previewing" @update:model-value="update({ voice: $event })" @preview="preview" />
            </div>
            <div class="row">
              <label for="dubWait" class="lbl">
                <span>{{ t("lblWait") }}</span>
                <small>{{ t("lblWaitHint") }}</small>
              </label>
              <ToggleSwitch id="dubWait" :model-value="settings.dubWait" @update:model-value="update({ dubWait: $event })" />
            </div>
            <div class="row">
              <label for="duck" class="lbl"><span>{{ t("lblDuck") }}</span></label>
              <span class="range">
                <input
                  id="duck"
                  type="range"
                  min="0"
                  max="0.6"
                  step="0.03"
                  :value="settings.duck"
                  @input="settings.duck = Number(($event.target as HTMLInputElement).value)"
                  @change="update({ duck: Number(($event.target as HTMLInputElement).value) })"
                />
                <output>{{ Math.round(settings.duck * 100) }}%</output>
              </span>
            </div>
          </div>
          <p v-if="note" class="msg err" role="alert">{{ note }}</p>
        </section>

        <section class="card" :aria-label="t('secSubs')">
          <div class="row">
            <label for="lang" class="lbl"><span>{{ t("lblLang") }}</span></label>
            <select id="lang" class="select" :value="settings.lang" @change="changeLang(($event.target as HTMLSelectElement).value)">
              <option v-for="l in TARGET_LANGS" :key="l.code" :value="l.code">{{ l.name }}</option>
            </select>
          </div>
          <div class="row">
            <label for="bilingual" class="lbl"><span>{{ t("lblBilingual") }}</span></label>
            <ToggleSwitch id="bilingual" :model-value="settings.bilingual" @update:model-value="update({ bilingual: $event })" />
          </div>
          <div class="row">
            <span class="lbl"><span>{{ t("lblPosition") }}</span></span>
            <SegmentedControl :model-value="settings.position" :options="positions" :label="t('lblPosition')" @update:model-value="update({ position: $event as any })" />
          </div>
          <div class="row">
            <span class="lbl"><span>{{ t("lblSize") }}</span></span>
            <SizeStepper :model-value="settings.size" @update:model-value="update({ size: $event })" />
          </div>
          <div class="row">
            <label for="bgo" class="lbl"><span>{{ t("lblBackground") }}</span></label>
            <span class="range">
              <input
                id="bgo"
                type="range"
                min="0"
                max="1"
                step="0.05"
                :value="settings.bgOpacity"
                @input="settings.bgOpacity = Number(($event.target as HTMLInputElement).value)"
                @change="update({ bgOpacity: Number(($event.target as HTMLInputElement).value) })"
              />
              <output>{{ Math.round(settings.bgOpacity * 100) }}%</output>
            </span>
          </div>
        </section>
      </template>
    </main>

    <footer class="foot">
      <span v-if="shortcut" class="kbd"><kbd>{{ shortcut }}</kbd></span>
      <span v-if="extVersion || appVersion" class="ver">
        <span v-if="extVersion">{{ t("verExtension", extVersion) }}</span>
        <span v-if="appVersion">{{ t("verApp", appVersion) }}</span>
      </span>
      <span class="spacer"></span>
      <button type="button" class="icon-btn" :title="t('btnSettings')" :aria-label="t('btnSettings')" @click="openOptions">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0" /><circle cx="16" cy="6" r="2" /><circle cx="10" cy="12" r="2" /><circle cx="18" cy="18" r="2" />
        </svg>
      </button>
      <button v-if="online" type="button" class="btn open" @click="openApp">
        {{ t("btnOpenApp") }}
        <svg class="flip" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9" /></svg>
      </button>
    </footer>
  </div>
</template>

<style>
html,
body {
  width: 360px;
}
body {
  overflow: hidden;
}
</style>

<style scoped>
.popup {
  display: flex;
  flex-direction: column;
  height: 580px;
  background:
    radial-gradient(140% 60% at 100% 0%, rgba(53, 80, 214, 0.38), transparent 60%),
    radial-gradient(90% 50% at 0% 100%, rgba(240, 146, 43, 0.08), transparent 60%),
    var(--lapis-950);
}

.head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--line);
}
.mark {
  flex: none;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.35));
}
.brand {
  min-width: 0;
}
.brand h1 {
  margin: 0;
  font: 600 19px/1.1 var(--display);
  letter-spacing: 0.01em;
}
.brand p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 11.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.note-old {
  margin: 0 0 10px;
  padding: 8px 10px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.6;
  background: rgba(240, 146, 43, 0.12);
  border: 1px solid rgba(240, 146, 43, 0.4);
}
.note-old a {
  color: inherit;
  font-weight: 600;
}
.conn {
  margin-inline-start: auto;
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 99px;
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 600;
}
.conn i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--faint);
}
.conn.ok {
  color: #BDF0D7;
}
.conn.ok i {
  background: var(--ok);
  box-shadow: 0 0 0 3px rgba(94, 211, 160, 0.2);
}
.conn.bad {
  color: #FFC7C0;
}
.conn.bad i {
  background: var(--bad);
}

.body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px 12px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.18) transparent;
}

.stage {
  margin-bottom: 12px;
}
.cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  width: 100%;
  min-height: 46px;
  margin-top: 12px;
  border: 0;
  border-radius: 13px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 700;
  color: var(--lapis-900);
  background: linear-gradient(180deg, #FFDE9A 0%, #FFC35A 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55), 0 10px 26px -10px rgba(240, 146, 43, 0.7);
  transition: filter 0.15s, transform 0.1s;
}
.cta:hover:not(:disabled) {
  filter: brightness(1.05);
}
.cta:active:not(:disabled) {
  transform: translateY(1px);
}
.cta:disabled {
  cursor: not-allowed;
  color: var(--faint);
  background: var(--surface-2);
  box-shadow: inset 0 0 0 1px var(--line);
}
.cta.busy-state:disabled {
  color: var(--lapis-900);
  background: linear-gradient(180deg, #FFDE9A 0%, #FFC35A 100%);
  opacity: 0.8;
}
.cta.stop {
  color: var(--parchment);
  background: var(--surface-2);
  box-shadow: inset 0 0 0 1px var(--line-strong);
}
.cta.stop svg {
  color: var(--bad);
}
.spin {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid currentColor;
  border-top-color: transparent;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.hint {
  margin: 8px 2px 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
  text-align: center;
}
.msg {
  margin: 10px 0 0;
  padding: 9px 11px;
  border-radius: 10px;
  font-size: 12.5px;
  line-height: 1.45;
}
.msg.err {
  background: rgba(255, 143, 132, 0.1);
  border: 1px solid rgba(255, 143, 132, 0.25);
  color: #FFCBC4;
}
.msg.info {
  background: rgba(154, 171, 245, 0.1);
  border: 1px solid rgba(154, 171, 245, 0.22);
  color: #D6DDFB;
}
.link {
  border: 0;
  padding: 0;
  background: none;
  color: var(--saffron-300);
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.card {
  margin-top: 10px;
  padding: 2px 12px;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--line);
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 46px;
  padding: 6px 0;
}
.row + .row,
.sub .row:first-child {
  border-top: 1px solid var(--line);
}
.lbl {
  display: flex;
  flex-direction: column;
  min-width: 0;
  cursor: pointer;
  font-weight: 500;
}
.lbl small {
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 400;
  line-height: 1.35;
}
.sub {
  transition: opacity 0.15s;
}
.sub .row {
  padding-inline-start: 12px;
  position: relative;
}
.sub .row::before {
  content: "";
  position: absolute;
  inset-inline-start: 0;
  top: 50%;
  width: 4px;
  height: 4px;
  transform: translateY(-50%) rotate(45deg);
  background: var(--saffron-300);
  opacity: 0.7;
}
.sub.dim {
  opacity: 0.42;
}
.range {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.range input {
  width: 116px;
}
.range output {
  min-width: 34px;
  text-align: end;
  color: var(--muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
#lang {
  min-width: 128px;
}

.offline {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 34px 8px 10px;
}
.glyph {
  display: grid;
  place-items: center;
  width: 60px;
  height: 60px;
  border-radius: 18px;
  color: var(--saffron-300);
  background: linear-gradient(160deg, rgba(53, 80, 214, 0.45), rgba(18, 26, 87, 0.6));
  border: 1px solid var(--line-strong);
}
.offline h2 {
  margin: 18px 0 6px;
  font: 600 19px/1.3 var(--display);
}
.offline p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}
.offline-actions {
  display: flex;
  gap: 8px;
  margin: 20px 0 14px;
}
.offline .small {
  font-size: 12px;
  color: var(--faint);
}

.skeleton .sk {
  border-radius: 12px;
  background: linear-gradient(90deg, var(--surface) 0%, var(--surface-2) 50%, var(--surface) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.2s linear infinite;
}
.sk.screen {
  aspect-ratio: 16 / 8.4;
}
.sk.cta {
  height: 46px;
  margin-top: 12px;
}
.sk.card {
  height: 150px;
  margin-top: 22px;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

.foot {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-top: 1px solid var(--line);
  background: rgba(10, 15, 58, 0.6);
}
/* Two short lines (extension, app) so they fit beside the shortcut and the buttons. */
.ver {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  color: var(--faint);
  font-size: 10.5px;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.kbd kbd {
  padding: 3px 5px;
  font-size: 10.5px;
}
.spacer {
  flex: 1;
}
.icon-btn {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.icon-btn:hover {
  color: var(--text);
  background: var(--surface-2);
}
.open {
  min-height: 34px;
  padding: 0 12px;
  font-size: 12.5px;
}
[dir="rtl"] .flip {
  transform: scaleX(-1);
}
</style>
