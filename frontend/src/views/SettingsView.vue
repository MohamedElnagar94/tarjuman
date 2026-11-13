<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { PhArrowsClockwise, PhDesktop, PhDeviceMobile, PhHardDrives, PhKeyboard, PhShieldCheck, PhPuzzlePiece, PhPaintBrush, PhSlidersHorizontal, PhSparkle, PhSpeakerHigh, PhWaveform } from "@phosphor-icons/vue";
import ShortcutList from "@/components/ShortcutList.vue";
import AiSettings from "@/components/settings/AiSettings.vue";
import PhonePairing from "@/components/settings/PhonePairing.vue";
import ExtensionTrust from "@/components/settings/ExtensionTrust.vue";
import StorageSettings from "@/components/settings/StorageSettings.vue";
import PrivacyFlow from "@/components/settings/PrivacyFlow.vue";
import DesktopLifecycle from "@/components/settings/DesktopLifecycle.vue";
import UpdatesPanel from "@/components/settings/UpdatesPanel.vue";
import PronounceEditor from "@/components/settings/PronounceEditor.vue";
import TranscriptionSettings from "@/components/settings/TranscriptionSettings.vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import SubtitleOverlay from "@/components/SubtitleOverlay.vue";
import type { Quality } from "@/api/types";
import { SUB_SIZE, usePrefs, type ThemePref, type UiLang } from "@/composables/prefs";
import { useVoices } from "@/composables/voices";
import { TARGET_LANGS } from "@/lib/langs";
import { FONTS } from "@/lib/fonts";

const { t } = useI18n();
const prefs = usePrefs();
const { voices } = useVoices();

onMounted(() => (document.title = t("settings.title") + " | " + t("app.name")));

const SECTIONS = [
  { id: "ai", icon: PhSparkle },
  { id: "transcription", icon: PhWaveform },
  { id: "phone", icon: PhDeviceMobile },
  { id: "extensions", icon: PhPuzzlePiece },
  { id: "pronounce", icon: PhSpeakerHigh },
  { id: "defaults", icon: PhSlidersHorizontal },
  { id: "appearance", icon: PhPaintBrush },
  { id: "updates", icon: PhArrowsClockwise },
  { id: "desktop", icon: PhDesktop },
  { id: "storage", icon: PhHardDrives },
  { id: "privacy", icon: PhShieldCheck },
  { id: "shortcuts", icon: PhKeyboard },
] as const;

const themeOptions = computed(() => [
  { value: "system" as ThemePref, label: t("appearance.system") },
  { value: "light" as ThemePref, label: t("appearance.light") },
  { value: "dark" as ThemePref, label: t("appearance.dark") },
]);
const langOptions = [
  { value: "ar" as UiLang, label: "العربية" },
  { value: "en" as UiLang, label: "English" },
];
const qualityOptions = [480, 720, 1080].map((q) => ({ value: q as Quality, label: q + "p" }));
</script>

<template>
  <div class="page settings">
    <header class="page__head">
      <h1 class="page__title">{{ t("settings.title") }}</h1>
      <p class="muted">{{ t("settings.lead") }}</p>
    </header>

    <div class="layout">
      <nav class="toc" :aria-label="t('settings.sections')">
        <a v-for="s in SECTIONS" :key="s.id" :href="'#' + s.id">
          <component :is="s.icon" :size="18" />
          {{ t("settings.s." + s.id) }}
        </a>
      </nav>

      <div class="sections">
        <section id="ai" class="panel sec" aria-labelledby="h-ai">
          <h2 id="h-ai" class="panel__title">{{ t("settings.s.ai") }}</h2>
          <AiSettings />
        </section>

        <section id="transcription" class="panel sec" aria-labelledby="h-asr">
          <h2 id="h-asr" class="panel__title">{{ t("settings.s.transcription") }}</h2>
          <TranscriptionSettings />
        </section>

        <section id="phone" class="panel sec" aria-labelledby="h-phone">
          <h2 id="h-phone" class="panel__title">{{ t("settings.s.phone") }}</h2>
          <PhonePairing />
        </section>

        <section id="extensions" class="panel sec" aria-labelledby="h-ext">
          <h2 id="h-ext" class="panel__title">{{ t("settings.s.extensions") }}</h2>
          <ExtensionTrust />
        </section>

        <section id="pronounce" class="panel sec" aria-labelledby="h-pr">
          <h2 id="h-pr" class="panel__title">{{ t("settings.s.pronounce") }}</h2>
          <PronounceEditor />
        </section>

        <section id="defaults" class="panel sec" aria-labelledby="h-def">
          <h2 id="h-def" class="panel__title">{{ t("settings.s.defaults") }}</h2>
          <p class="panel__lead">{{ t("settings.defaultsLead") }}</p>
          <div class="opts">
            <div class="opt">
              <label class="opt__label" for="d-tl">{{ t("watch.opts.tl") }}</label>
              <select id="d-tl" v-model="prefs.tl" class="select sel">
                <option v-for="l in TARGET_LANGS" :key="l" :value="l">{{ t("langs." + l) }}</option>
              </select>
            </div>
            <div class="opt">
              <label class="opt__label" for="d-voice">{{ t("dub.voice") }}<small>{{ t("settings.voiceHint") }}</small></label>
              <select id="d-voice" v-model="prefs.voice" class="select sel">
                <option value="auto">{{ t("dub.voiceAuto") }}</option>
                <option v-for="v in voices" :key="v.id" :value="v.id">{{ v.name }} · {{ v.accent }}</option>
              </select>
            </div>
            <div class="opt">
              <span class="opt__label">{{ t("export.quality") }}</span>
              <SegmentedControl v-model="prefs.quality" :options="qualityOptions" :label="t('export.quality')" size="sm" />
            </div>
            <div class="opt">
              <label class="opt__label" for="d-wait">{{ t("dub.wait") }}<small>{{ t("dub.waitHint") }}</small></label>
              <ToggleSwitch id="d-wait" v-model="prefs.dubWait" />
            </div>
            <div class="opt">
              <label class="opt__label" for="d-embed">{{ t("export.dub.embed") }}</label>
              <ToggleSwitch id="d-embed" v-model="prefs.embedSubs" />
            </div>
            <div class="opt">
              <label class="opt__label" for="d-remove">{{ t("export.dub.remove") }}</label>
              <ToggleSwitch id="d-remove" v-model="prefs.removeVoice" />
            </div>
          </div>
        </section>

        <section id="appearance" class="panel sec" aria-labelledby="h-app">
          <h2 id="h-app" class="panel__title">{{ t("settings.s.appearance") }}</h2>
          <div class="opts">
            <div class="opt">
              <span class="opt__label">{{ t("appearance.theme") }}</span>
              <SegmentedControl v-model="prefs.theme" :options="themeOptions" :label="t('appearance.theme')" size="sm" />
            </div>
            <div class="opt">
              <span class="opt__label">{{ t("appearance.language") }}</span>
              <SegmentedControl v-model="prefs.uiLang" :options="langOptions" :label="t('appearance.language')" size="sm" />
            </div>
            <div class="opt">
              <label class="opt__label" for="a-size">{{ t("watch.opts.size") }}<small class="mono">{{ prefs.size }}px</small></label>
              <input id="a-size" v-model.number="prefs.size" class="range" type="range" :min="SUB_SIZE.min" :max="SUB_SIZE.max" :step="SUB_SIZE.step" />
            </div>
            <div class="opt">
              <label class="opt__label" for="a-font">{{ t("appearance.font") }}</label>
              <select id="a-font" v-model="prefs.font" class="select sel">
                <option v-for="f in FONTS" :key="f.id" :value="f.id" :style="{ fontFamily: f.family }">{{ t("fonts." + f.id) }}</option>
              </select>
            </div>
            <div class="opt">
              <label class="opt__label" for="a-bgo">{{ t("watch.opts.background") }}</label>
              <input id="a-bgo" v-model.number="prefs.bgo" class="range" type="range" min="0" max="1" step="0.05" />
            </div>
          </div>
          <div class="sample" aria-hidden="true">
            <SubtitleOverlay
              src="This is how your subtitles will look."
              :text="t('settings.sample')"
              :bilingual="prefs.bilingual"
              position="bottom"
              :size="prefs.size"
              :font="prefs.font"
              :bgo="prefs.bgo"
              :rtl="prefs.tl === 'ar'"
              inline
            />
          </div>
        </section>

        <section id="updates" class="panel sec" aria-labelledby="h-updates">
          <h2 id="h-updates" class="panel__title">{{ t("settings.s.updates") }}</h2>
          <UpdatesPanel />
        </section>

        <section id="desktop" class="panel sec" aria-labelledby="h-desktop">
          <h2 id="h-desktop" class="panel__title">{{ t("settings.s.desktop") }}</h2>
          <DesktopLifecycle />
        </section>

        <section id="storage" class="panel sec" aria-labelledby="h-storage">
          <h2 id="h-storage" class="panel__title">{{ t("settings.s.storage") }}</h2>
          <StorageSettings />
        </section>

        <section id="privacy" class="panel sec" aria-labelledby="h-privacy">
          <h2 id="h-privacy" class="panel__title">{{ t("settings.s.privacy") }}</h2>
          <PrivacyFlow />
        </section>

        <section id="shortcuts" class="panel sec" aria-labelledby="h-keys">
          <h2 id="h-keys" class="panel__title">{{ t("settings.s.shortcuts") }}</h2>
          <p class="panel__lead">{{ t("settings.shortcutsLead") }}</p>
          <div class="keys"><ShortcutList /></div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: var(--s-8);
  align-items: start;
}
.toc {
  position: sticky;
  top: calc(var(--header-h) + var(--s-6));
  display: grid;
  gap: 2px;
}
.toc a {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 12px;
  border-radius: var(--r-sm);
  color: var(--text-2);
  text-decoration: none;
  font-size: var(--fs-sm);
}
.toc a:hover {
  background: var(--surface-1);
  color: var(--text);
}
.sections {
  max-width: 820px;
  display: grid;
  gap: var(--s-6);
}
.sec {
  scroll-margin-top: calc(var(--header-h) + 16px);
}
.sec > .panel__title {
  margin-bottom: var(--s-3);
}
.opts {
  margin-top: var(--s-2);
}
.sel {
  width: auto;
  max-width: 240px;
}
.range {
  width: 180px;
}
.sample {
  margin-top: var(--s-4);
  padding: var(--s-8) var(--s-4) var(--s-5);
  border-radius: var(--r-md);
  background:
    radial-gradient(90% 80% at 80% 0%, rgba(255, 210, 122, 0.12), transparent 60%),
    linear-gradient(160deg, var(--lapis-700), var(--lapis-900));
}
.keys {
  margin-top: var(--s-4);
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .toc {
    position: static;
    display: flex;
    overflow-x: auto;
    gap: 6px;
    scrollbar-width: none;
  }
  .toc a {
    flex: none;
    border: 1px solid var(--line-2);
    border-radius: var(--r-pill);
    min-height: 36px;
  }
}
@media (max-width: 480px) {
  .opt {
    flex-wrap: wrap;
  }
  .range {
    width: 100%;
  }
}
</style>
