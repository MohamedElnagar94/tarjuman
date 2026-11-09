<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { t } from "@/shared/i18n";
import { send } from "@/shared/messages";
import { TARGET_LANGS, SIZE_MIN, SIZE_MAX, DEFAULT_SETTINGS } from "@/shared/settings";
import { PORTS } from "@/shared/server";
import { useExtension } from "@/ui/useExtension";
import { shortcutText } from "@/ui/errors";
import ToggleSwitch from "@/ui/ToggleSwitch.vue";
import SegmentedControl from "@/ui/SegmentedControl.vue";
import SubtitlePreview from "@/ui/SubtitlePreview.vue";
import VoicePicker from "@/ui/VoicePicker.vue";

const { settings, status, loaded, voices, previewing, refresh, update, loadVoices, previewVoice } = useExtension();

const REPO = "https://github.com/MohamedElnagar94/tarjuman";
const PRIVACY = "https://mohamedelnagar94.github.io/tarjuman/privacy.html";

const shortcut = ref("");
const voiceNote = ref("");
const allSites = ref(false);
const sites = ref<string[]>([]);
const address = ref("");
const testing = ref(false);
const test = ref<{ ok: boolean; text: string } | null>(null);
const saved = ref(false);

const online = computed(() => !!status.value?.health);
const health = computed(() => status.value?.health || null);
const portRange = `${PORTS[0]}–${PORTS[PORTS.length - 1]}`;

const positions = computed(() => [
  { value: "bottom", label: t("posBottom") },
  { value: "top", label: t("posTop") },
]);

const sections = computed(() => [
  { id: "subtitles", label: t("secSubs") },
  { id: "dubbing", label: t("secDub") },
  { id: "sites", label: t("secSites") },
  { id: "connection", label: t("secConnection") },
  { id: "shortcut", label: t("secShortcut") },
  { id: "about", label: t("secAbout") },
]);

async function loadPermissions() {
  const all = await chrome.permissions.getAll();
  const origins = (all.origins || []).filter((o) => !/^http:\/\/(127\.0\.0\.1|localhost)\//.test(o));
  allSites.value = origins.includes("<all_urls>") || origins.includes("*://*/*");
  sites.value = origins.filter((o) => o !== "<all_urls>" && o !== "*://*/*");
}

async function setAllSites(on: boolean) {
  try {
    if (on) await chrome.permissions.request({ origins: ["<all_urls>"] });
    else await chrome.permissions.remove({ origins: ["<all_urls>"] });
  } catch {}
  await loadPermissions();
}

async function removeSite(o: string) {
  try {
    await chrome.permissions.remove({ origins: [o] });
  } catch {}
  await loadPermissions();
}

const siteName = (o: string) => o.replace(/^\w+:\/\//, "").replace(/\/\*$/, "");

async function changeLang(lang: string) {
  await update({ lang, voice: "" });
  await loadVoices();
}

async function preview() {
  voiceNote.value = "";
  if (!(await previewVoice())) voiceNote.value = t("errVoice");
}

function describe(r: any) {
  if (r.ok) return t("testOk", [String(r.health?.version || "?"), r.base]);
  if (r.code === "BAD_ADDRESS") return t("errBadAddress");
  return t("testFail");
}

async function testConnection() {
  testing.value = true;
  test.value = null;
  const r = await send("test-connection", { url: address.value.trim() });
  test.value = { ok: !!r.ok, text: describe(r) };
  testing.value = false;
}

async function saveAddress() {
  test.value = null;
  const r = await send("set-override", { url: address.value.trim() });
  if (!r.ok) {
    test.value = { ok: false, text: describe(r) };
    return;
  }
  saved.value = true;
  setTimeout(() => (saved.value = false), 1800);
  await refresh();
  if (online.value) await loadVoices();
}

async function resetAddress() {
  address.value = "";
  await saveAddress();
}

function resetLook() {
  update({ size: DEFAULT_SETTINGS.size, position: DEFAULT_SETTINGS.position, bgOpacity: DEFAULT_SETTINGS.bgOpacity, bilingual: DEFAULT_SETTINGS.bilingual });
}

onMounted(async () => {
  shortcut.value = await shortcutText();
  await Promise.all([refresh(), loadPermissions()]);
  address.value = status.value?.override || "";
  if (online.value) await loadVoices();
  chrome.permissions.onAdded.addListener(loadPermissions);
  chrome.permissions.onRemoved.addListener(loadPermissions);
});
</script>

<template>
  <div class="page">
    <aside class="side">
      <div class="brand">
        <img src="/icons/icon.svg" alt="" width="40" height="40" />
        <div>
          <strong>{{ t("extShortName") }}</strong>
          <span>{{ t("optionsTitle") }}</span>
        </div>
      </div>
      <nav :aria-label="t('optionsTitle')">
        <a v-for="s in sections" :key="s.id" :href="'#' + s.id">{{ s.label }}</a>
      </nav>
      <div class="conn" :class="{ ok: online, bad: loaded && !online }">
        <i aria-hidden="true"></i>
        <span>{{ !loaded ? t("connSearching") : online ? t("connOnline") : t("connOffline") }}</span>
      </div>
    </aside>

    <main class="main">
      <header class="intro">
        <h1>{{ t("optionsTitle") }}</h1>
        <p>{{ t("optionsIntro") }}</p>
      </header>

      <section id="subtitles" class="panel">
        <div class="panel-head">
          <h2>{{ t("secSubs") }}</h2>
          <button type="button" class="btn ghost" @click="resetLook">{{ t("btnReset") }}</button>
        </div>
        <div class="split">
          <SubtitlePreview :settings="settings" :scale="0.9" :label="t('previewLabel')" />
          <div class="fields">
            <div class="field">
              <label for="lang">{{ t("lblLang") }}</label>
              <select id="lang" class="select" :value="settings.lang" @change="changeLang(($event.target as HTMLSelectElement).value)">
                <option v-for="l in TARGET_LANGS" :key="l.code" :value="l.code">{{ l.name }}</option>
              </select>
            </div>
            <div class="field">
              <label for="size">{{ t("lblSize") }} <output>{{ settings.size }}px</output></label>
              <input
                id="size"
                type="range"
                :min="SIZE_MIN"
                :max="SIZE_MAX"
                step="1"
                :value="settings.size"
                @input="settings.size = Number(($event.target as HTMLInputElement).value)"
                @change="update({ size: Number(($event.target as HTMLInputElement).value) })"
              />
            </div>
            <div class="field">
              <label for="bgo">{{ t("lblBackground") }} <output>{{ Math.round(settings.bgOpacity * 100) }}%</output></label>
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
            </div>
            <div class="field inline">
              <span class="label">{{ t("lblPosition") }}</span>
              <SegmentedControl :model-value="settings.position" :options="positions" :label="t('lblPosition')" @update:model-value="update({ position: $event as any })" />
            </div>
            <div class="field inline">
              <label for="bilingual">{{ t("lblBilingual") }}</label>
              <ToggleSwitch id="bilingual" :model-value="settings.bilingual" @update:model-value="update({ bilingual: $event })" />
            </div>
          </div>
        </div>
      </section>

      <section id="dubbing" class="panel">
        <div class="panel-head"><h2>{{ t("secDub") }}</h2></div>
        <div class="rows">
          <div class="row">
            <label for="dub" class="lbl"><span>{{ t("lblDub") }}</span><small>{{ t("lblDubHint") }}</small></label>
            <ToggleSwitch id="dub" :model-value="settings.dub" @update:model-value="update({ dub: $event })" />
          </div>
          <div class="row">
            <label for="voice" class="lbl"><span>{{ t("lblVoice") }}</span><small>{{ online ? t("lblVoiceHint") : t("lblVoiceOffline") }}</small></label>
            <VoicePicker id="voice" :model-value="settings.voice" :voices="voices" :previewing="previewing" @update:model-value="update({ voice: $event })" @preview="preview" />
          </div>
          <p v-if="voiceNote" class="msg err" role="alert">{{ voiceNote }}</p>
          <div class="row">
            <label for="dubWait" class="lbl"><span>{{ t("lblWait") }}</span><small>{{ t("lblWaitHint") }}</small></label>
            <ToggleSwitch id="dubWait" :model-value="settings.dubWait" @update:model-value="update({ dubWait: $event })" />
          </div>
          <div class="row">
            <label for="duck" class="lbl"><span>{{ t("lblDuck") }}</span><small>{{ t("lblDuckHint") }}</small></label>
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
      </section>

      <section id="sites" class="panel">
        <div class="panel-head"><h2>{{ t("secSites") }}</h2></div>
        <p class="lead">{{ t("sitesIntro") }}</p>
        <div class="rows">
          <div class="row">
            <label for="allSites" class="lbl"><span>{{ t("lblAllSites") }}</span><small>{{ t("lblAllSitesHint") }}</small></label>
            <ToggleSwitch id="allSites" :model-value="allSites" @update:model-value="setAllSites" />
          </div>
        </div>
        <h3>{{ t("sitesGranted") }}</h3>
        <ul v-if="sites.length" class="sites">
          <li v-for="o in sites" :key="o">
            <span dir="ltr">{{ siteName(o) }}</span>
            <button type="button" class="btn ghost" @click="removeSite(o)">{{ t("btnRemove") }}</button>
          </li>
        </ul>
        <p v-else class="empty">{{ t("sitesNone") }}</p>
      </section>

      <section id="connection" class="panel">
        <div class="panel-head"><h2>{{ t("secConnection") }}</h2></div>
        <div class="status" :class="{ ok: online, bad: loaded && !online }">
          <i aria-hidden="true"></i>
          <div>
            <strong>{{ online ? t("connOnlineLong", [String(health?.version || "?")]) : t("connOfflineLong") }}</strong>
            <span v-if="online" dir="ltr">{{ status?.server }}</span>
            <span v-else>{{ t("connOfflineHint") }}</span>
          </div>
          <a v-if="!online" class="btn" href="welcome.html" target="_blank">{{ t("btnHowToStart") }}</a>
        </div>
        <details class="advanced" :open="!!status?.override || undefined">
          <summary>{{ t("advanced") }}</summary>
          <label for="addr" class="label">{{ t("lblServerAddress") }}</label>
          <p class="small">{{ t("lblServerAddressHint", [portRange]) }}</p>
          <div class="addr">
            <input id="addr" v-model="address" class="input" dir="ltr" spellcheck="false" autocomplete="off" :placeholder="t('addrPlaceholder')" @keydown.enter="saveAddress" />
            <button type="button" class="btn" :disabled="testing" @click="testConnection">{{ testing ? t("connSearching") : t("btnTest") }}</button>
            <button type="button" class="btn primary" @click="saveAddress">{{ saved ? t("saved") : t("btnSave") }}</button>
            <button v-if="status?.override" type="button" class="btn ghost" @click="resetAddress">{{ t("btnAuto") }}</button>
          </div>
          <p v-if="test" class="msg" :class="test.ok ? 'ok' : 'err'" role="status">{{ test.text }}</p>
        </details>
      </section>

      <section id="shortcut" class="panel">
        <div class="panel-head"><h2>{{ t("secShortcut") }}</h2></div>
        <div class="rows">
          <div class="row">
            <span class="lbl"><span>{{ t("lblShortcut") }}</span><small>{{ t("lblShortcutHint") }}</small></span>
            <span class="keys">
              <kbd v-if="shortcut">{{ shortcut }}</kbd>
              <span v-else class="small">{{ t("shortcutNone") }}</span>
              <button type="button" class="btn" @click="send('open-shortcuts')">{{ t("btnChange") }}</button>
            </span>
          </div>
        </div>
      </section>

      <section id="about" class="panel">
        <div class="panel-head"><h2>{{ t("secAbout") }}</h2></div>
        <p class="lead">{{ t("aboutBody") }}</p>
        <div class="links">
          <a class="btn" :href="REPO" target="_blank" rel="noopener">{{ t("linkGitHub") }}</a>
          <a class="btn" href="welcome.html" target="_blank">{{ t("linkWelcome") }}</a>
          <a class="btn ghost" :href="PRIVACY" target="_blank" rel="noopener">{{ t("linkPrivacy") }}</a>
        </div>
        <p class="small ver">{{ t("extShortName") }} {{ status?.version }}</p>
      </section>
    </main>
  </div>
</template>

<style>
body {
  background:
    radial-gradient(80% 50% at 85% 0%, rgba(53, 80, 214, 0.3), transparent 60%),
    radial-gradient(60% 40% at 0% 100%, rgba(240, 146, 43, 0.06), transparent 60%),
    var(--lapis-950);
  background-attachment: fixed;
  min-height: 100vh;
  font-size: 14px;
}
html {
  scroll-behavior: smooth;
  scroll-padding-top: 24px;
}
</style>

<style scoped>
.page {
  display: grid;
  grid-template-columns: 240px minmax(0, 820px);
  gap: 48px;
  justify-content: center;
  padding: 40px 32px 80px;
}
.side {
  position: sticky;
  top: 40px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand strong {
  display: block;
  font: 600 20px/1.1 var(--display);
}
.brand span {
  color: var(--muted);
  font-size: 12.5px;
}
nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
nav a {
  padding: 8px 12px;
  border-radius: 9px;
  color: var(--muted);
  text-decoration: none;
  font-weight: 500;
  border-inline-start: 2px solid transparent;
}
nav a:hover {
  color: var(--text);
  background: var(--surface);
  border-inline-start-color: var(--saffron-300);
}
.conn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: 99px;
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 12.5px;
  font-weight: 600;
}
.conn i,
.status i {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 50%;
  background: var(--faint);
}
.conn.ok i,
.status.ok i {
  background: var(--ok);
  box-shadow: 0 0 0 4px rgba(94, 211, 160, 0.18);
}
.conn.bad i,
.status.bad i {
  background: var(--bad);
  box-shadow: 0 0 0 4px rgba(255, 143, 132, 0.15);
}

.intro h1 {
  margin: 0;
  font: 600 32px/1.2 var(--display);
}
.intro p {
  margin: 8px 0 28px;
  color: var(--muted);
  max-width: 60ch;
  line-height: 1.6;
}
.panel {
  padding: 22px 24px;
  margin-bottom: 18px;
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 1px solid var(--line);
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
h2 {
  margin: 0;
  font: 600 18px/1.3 var(--display);
  display: flex;
  align-items: center;
  gap: 10px;
}
h2::before {
  content: "";
  width: 8px;
  height: 8px;
  transform: rotate(45deg);
  border-radius: 1.5px;
  background: linear-gradient(135deg, var(--saffron-300), var(--saffron-500));
}
h3 {
  margin: 18px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}
.lead {
  margin: -4px 0 12px;
  color: var(--muted);
  line-height: 1.6;
  max-width: 68ch;
}
.split {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}
.fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field label,
.field .label {
  font-weight: 500;
  display: flex;
  justify-content: space-between;
}
.field output {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.field.inline {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}
.field input[type="range"] {
  width: 100%;
}
.rows .row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 56px;
  padding: 8px 0;
}
.rows .row + .row {
  border-top: 1px solid var(--line);
}
.lbl {
  display: flex;
  flex-direction: column;
  cursor: pointer;
  font-weight: 500;
}
.lbl small {
  color: var(--muted);
  font-weight: 400;
  font-size: 12.5px;
}
.range {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.range input {
  width: 180px;
}
.range output {
  min-width: 40px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.sites {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius);
}
.sites li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px 6px 14px;
}
.sites li + li {
  border-top: 1px solid var(--line);
}
.empty,
.small {
  color: var(--faint);
  font-size: 12.5px;
  margin: 0;
}
.status {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid var(--line);
}
.status div {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.status span {
  color: var(--muted);
  font-size: 12.5px;
}
.advanced {
  margin-top: 14px;
}
.advanced summary {
  cursor: pointer;
  color: var(--muted);
  font-weight: 600;
  padding: 6px 0;
}
.advanced summary:hover {
  color: var(--text);
}
.advanced .label {
  display: block;
  margin-top: 10px;
  font-weight: 500;
}
.advanced .small {
  margin: 2px 0 10px;
}
.addr {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.addr .input {
  flex: 1;
  min-width: 220px;
  min-height: 36px;
}
.msg {
  margin: 10px 0 0;
  padding: 9px 12px;
  border-radius: 10px;
  font-size: 13px;
}
.msg.ok {
  background: rgba(94, 211, 160, 0.1);
  border: 1px solid rgba(94, 211, 160, 0.25);
  color: #C5F2DD;
}
.msg.err {
  background: rgba(255, 143, 132, 0.1);
  border: 1px solid rgba(255, 143, 132, 0.25);
  color: #FFCBC4;
}
.keys {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.links {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ver {
  margin-top: 14px;
}

@media (max-width: 900px) {
  .page {
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
    padding: 24px 16px 60px;
  }
  .side {
    position: static;
  }
  nav {
    flex-direction: row;
    flex-wrap: wrap;
  }
  .split {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
