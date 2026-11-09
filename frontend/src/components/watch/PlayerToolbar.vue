<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  PhArrowsOut,
  PhClosedCaptioning,
  PhKeyboard,
  PhMicrophoneStage,
  PhPause,
  PhPlay,
  PhRepeatOnce,
  PhSkipBack,
  PhSkipForward,
  PhTranslate,
} from "@phosphor-icons/vue";
import { liveDub, toggleLiveDub } from "@/composables/liveDub";
import { usePrefs } from "@/composables/prefs";
import { session, stepLine, togglePlay } from "@/composables/session";
import { formatTime } from "@/lib/time";

const emit = defineEmits<{ fullscreen: []; shortcuts: [] }>();
const { t } = useI18n();
const prefs = usePrefs();
const disabled = computed(() => !session.ready);
const rtl = computed(() => prefs.uiLang === "ar");
const total = computed(() => session.lengthSeconds);
</script>

<template>
  <div class="tb" role="toolbar" :aria-label="t('watch.toolbar')">
    <div class="tb__group">
      <button class="btn btn--icon tb__play" type="button" :disabled="disabled" :aria-label="session.playing ? t('watch.pause') : t('watch.play')" :title="(session.playing ? t('watch.pause') : t('watch.play')) + ' (K)'" @click="togglePlay">
        <PhPause v-if="session.playing" :size="20" weight="fill" />
        <PhPlay v-else :size="20" weight="fill" />
      </button>
      <!-- In RTL the "previous line" control sits on the right, like the arrow keys. -->
      <button class="btn btn--quiet btn--icon" type="button" :disabled="disabled" :aria-label="t('watch.prevLine')" :title="t('watch.prevLine')" @click="stepLine(-1)">
        <PhSkipForward v-if="rtl" :size="18" />
        <PhSkipBack v-else :size="18" />
      </button>
      <button class="btn btn--quiet btn--icon" type="button" :disabled="disabled" :aria-label="t('watch.repeatLine')" :title="t('watch.repeatLine') + ' (R)'" @click="stepLine(0)">
        <PhRepeatOnce :size="18" />
      </button>
      <button class="btn btn--quiet btn--icon" type="button" :disabled="disabled" :aria-label="t('watch.nextLine')" :title="t('watch.nextLine')" @click="stepLine(1)">
        <PhSkipBack v-if="rtl" :size="18" />
        <PhSkipForward v-else :size="18" />
      </button>
      <span class="clock mono ltr" aria-live="off">
        {{ formatTime(session.time) }}<template v-if="total"> / {{ formatTime(total) }}</template>
      </span>
    </div>

    <div class="tb__group">
      <button class="btn btn--quiet btn--sm" :class="{ 'btn--on': prefs.show }" type="button" :aria-pressed="prefs.show" :title="t('watch.opts.show') + ' (C)'" @click="prefs.show = !prefs.show">
        <PhClosedCaptioning :size="18" />
        <span class="lbl">{{ t("watch.tb.subs") }}</span>
      </button>
      <button class="btn btn--quiet btn--sm" :class="{ 'btn--on': prefs.bilingual }" type="button" :aria-pressed="prefs.bilingual" :title="t('watch.opts.bilingual') + ' (B)'" @click="prefs.bilingual = !prefs.bilingual">
        <PhTranslate :size="18" />
        <span class="lbl">{{ t("watch.tb.bilingual") }}</span>
      </button>
      <button class="btn btn--sm dub" :class="liveDub.on ? 'btn--on' : 'btn--primary'" type="button" :disabled="disabled" :aria-pressed="liveDub.on" :title="t('dub.live.toggle') + ' (D)'" @click="toggleLiveDub">
        <PhMicrophoneStage :size="18" />
        <span>{{ liveDub.on ? t("dub.live.stop") : t("dub.live.start") }}</span>
      </button>
      <button class="btn btn--quiet btn--icon btn--sm hide-sm" type="button" :aria-label="t('shortcuts.title')" :title="t('shortcuts.title') + ' (?)'" @click="emit('shortcuts')">
        <PhKeyboard :size="18" />
      </button>
      <button class="btn btn--quiet btn--icon btn--sm" type="button" :disabled="disabled" :aria-label="t('watch.fullscreen')" :title="t('watch.fullscreen') + ' (F)'" @click="emit('fullscreen')">
        <PhArrowsOut :size="18" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.tb {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  flex-wrap: wrap;
  padding: var(--s-2) 0;
}
.tb__group {
  display: flex;
  align-items: center;
  gap: 2px;
}
.tb__play {
  --btn-bg: var(--surface-2);
  border-radius: 50%;
  margin-inline-end: 4px;
}
.clock {
  margin-inline-start: var(--s-3);
  font-size: var(--fs-xs);
  color: var(--text-2);
  white-space: nowrap;
}
.dub {
  margin-inline: 4px;
}
@media (max-width: 759px) {
  .tb {
    padding: var(--s-2) var(--s-3);
  }
  .lbl,
  .hide-sm {
    display: none;
  }
}
</style>
