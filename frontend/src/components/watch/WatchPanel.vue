<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhMicrophoneStage, PhMinus, PhPlus, PhSpeakerHigh } from "@phosphor-icons/vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { errText } from "@/i18n";
import { errorCode } from "@/api/client";
import { liveDub, restartLiveDub, setDubOptions, toggleLiveDub } from "@/composables/liveDub";
import { SUB_SIZE, usePrefs } from "@/composables/prefs";
import { applySpeed, loadVideo, session } from "@/composables/session";
import { toast } from "@/composables/toast";
import { playTts, useVoices, VOICE_SAMPLES, liveVoiceId } from "@/composables/voices";
import { TARGET_LANGS } from "@/lib/langs";

const { t } = useI18n();
const prefs = usePrefs();
const { voices, failed } = useVoices();
const previewing = ref(false);

const posOptions = computed(() => [
  { value: "bottom" as const, label: t("watch.opts.bottom") },
  { value: "top" as const, label: t("watch.opts.top") },
]);
const speedOptions = [0.75, 1, 1.25, 1.5].map((v) => ({ value: v, label: String(v) + "×" }));

watch(() => prefs.speed, applySpeed);

function changeTl(e: Event) {
  prefs.tl = (e.target as HTMLSelectElement).value;
  if (session.link) void loadVideo(session.link);
}
function changeVoice(e: Event) {
  prefs.voice = (e.target as HTMLSelectElement).value;
  restartLiveDub();
}
watch(() => prefs.dubWait, (wait) => setDubOptions({ wait }));
watch(() => prefs.bgVol, (duck) => setDubOptions({ duck }));

async function preview() {
  previewing.value = true;
  try {
    await playTts(VOICE_SAMPLES[prefs.tl] || VOICE_SAMPLES.en!, prefs.tl, liveVoiceId(prefs.voice));
  } catch (e) {
    toast(errText(errorCode(e)), { tone: "danger" });
  } finally {
    previewing.value = false;
  }
}

const bgLabel = computed(() => (prefs.bgVol > 0 ? t("dub.bg.level", { pct: Math.round(prefs.bgVol * 100) }) : t("dub.bg.muted")));
</script>

<template>
  <div class="task-stack">
    <section class="task" aria-labelledby="g-subs">
      <h3 id="g-subs" class="task__title">{{ t("watch.opts.title") }}</h3>
      <div class="opt">
        <label class="opt__label" for="o-tl">{{ t("watch.opts.tl") }}</label>
        <select id="o-tl" class="select" :value="prefs.tl" @change="changeTl">
          <option v-for="l in TARGET_LANGS" :key="l" :value="l">{{ t("langs." + l) }}</option>
        </select>
      </div>
      <div class="opt">
        <label class="opt__label" for="o-show">{{ t("watch.opts.show") }}<small>{{ t("watch.opts.showHint") }}</small></label>
        <ToggleSwitch id="o-show" v-model="prefs.show" />
      </div>
      <div class="opt">
        <label class="opt__label" for="o-bi">{{ t("watch.opts.bilingual") }}<small>{{ t("watch.opts.bilingualHint") }}</small></label>
        <ToggleSwitch id="o-bi" v-model="prefs.bilingual" />
      </div>
      <div class="opt">
        <span class="opt__label">{{ t("watch.opts.position") }}</span>
        <SegmentedControl v-model="prefs.position" :options="posOptions" :label="t('watch.opts.position')" size="sm" />
      </div>
      <div class="opt">
        <span class="opt__label">{{ t("watch.opts.size") }}</span>
        <div class="step" role="group" :aria-label="t('watch.opts.size')">
          <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('watch.opts.smaller')" :disabled="prefs.size <= SUB_SIZE.min" @click="prefs.size = Math.max(SUB_SIZE.min, prefs.size - SUB_SIZE.step)"><PhMinus :size="14" /></button>
          <output class="mono">{{ prefs.size }}</output>
          <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('watch.opts.bigger')" :disabled="prefs.size >= SUB_SIZE.max" @click="prefs.size = Math.min(SUB_SIZE.max, prefs.size + SUB_SIZE.step)"><PhPlus :size="14" /></button>
        </div>
      </div>
      <div class="opt">
        <label class="opt__label" for="o-bgo">{{ t("watch.opts.background") }}</label>
        <input id="o-bgo" v-model.number="prefs.bgo" class="range" type="range" min="0" max="1" step="0.05" />
      </div>
      <div class="opt">
        <span class="opt__label">{{ t("watch.opts.speed") }}</span>
        <SegmentedControl v-model="prefs.speed" :options="speedOptions" :label="t('watch.opts.speed')" size="sm" />
      </div>
    </section>

    <section class="task" aria-labelledby="g-dub">
      <h3 id="g-dub" class="task__title">{{ t("dub.live.title") }}</h3>
      <p class="task__lead">{{ t("dub.live.lead") }}</p>
      <div class="opt">
        <label class="opt__label" for="o-voice">{{ t("dub.voice") }}</label>
        <div class="opt__control">
          <select id="o-voice" class="select voice" :value="prefs.voice" @change="changeVoice">
            <option value="auto">{{ t("dub.voiceAuto") }}</option>
            <option v-for="v in voices" :key="v.id" :value="v.id">{{ v.name }} · {{ v.accent }}</option>
          </select>
          <button type="button" class="btn btn--outline btn--icon btn--sm" :disabled="previewing" :aria-label="t('dub.listen')" :title="t('dub.listen')" @click="preview"><PhSpeakerHigh :size="16" /></button>
        </div>
      </div>
      <p v-if="failed" class="field__error">{{ t("dub.voicesFailed") }}</p>
      <div class="opt">
        <label class="opt__label" for="o-bg">{{ t("dub.bg.label") }}<small>{{ bgLabel }}</small></label>
        <input id="o-bg" v-model.number="prefs.bgVol" class="range" type="range" min="0" max="0.5" step="0.02" />
      </div>
      <div class="opt">
        <label class="opt__label" for="o-wait">{{ t("dub.wait") }}<small>{{ t("dub.waitHint") }}</small></label>
        <ToggleSwitch id="o-wait" v-model="prefs.dubWait" />
      </div>
      <div class="actions">
        <button type="button" class="btn" :class="liveDub.on ? 'btn--on' : 'btn--primary'" :disabled="!session.ready" @click="toggleLiveDub">
          <PhMicrophoneStage :size="18" />
          {{ liveDub.on ? t("dub.live.stop") : t("dub.live.start") }}
        </button>
        <RouterLink class="btn btn--quiet" to="/settings#pronounce">{{ t("dub.dictionary") }}</RouterLink>
      </div>
      <p v-if="liveDub.on && liveDub.sentence" class="speaking" :dir="session.tl === 'ar' ? 'rtl' : 'ltr'">{{ liveDub.sentence }}</p>
    </section>
  </div>
</template>

<style scoped>
.step {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: var(--r-sm);
  background: var(--surface-2);
  border: 1px solid var(--line);
}
.step output {
  min-width: 30px;
  text-align: center;
  font-size: var(--fs-sm);
}
.select {
  width: auto;
  max-width: 200px;
  min-height: 36px;
}
.voice {
  max-width: 190px;
}
.range {
  width: 150px;
}
.speaking {
  margin-top: var(--s-3);
  padding: var(--s-3);
  border-radius: var(--r-sm);
  background: var(--bg);
  border-inline-start: 2px solid var(--accent-strong);
  font-size: var(--fs-sm);
  color: var(--text-2);
}
</style>
