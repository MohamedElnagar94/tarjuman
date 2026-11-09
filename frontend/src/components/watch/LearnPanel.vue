<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhCursorClick } from "@phosphor-icons/vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api } from "@/api/client";
import type { VocabItem } from "@/api/types";
import { vocabVersion } from "@/composables/lookup";
import { usePrefs } from "@/composables/prefs";
import { armLoop, seekTo, session } from "@/composables/session";
import { formatTime } from "@/lib/time";

const { t } = useI18n();
const prefs = usePrefs();
const words = ref<VocabItem[]>([]);

async function loadWords() {
  try {
    words.value = (await api.vocab()).items || [];
  } catch {
    words.value = [];
  }
}
onMounted(loadWords);
watch(() => vocabVersion.n, loadWords);

const mine = computed(() => words.value.filter((w) => w.videoId === session.videoId).sort((a, b) => a.t - b.t));
watch(() => prefs.loop, (on) => on && armLoop());
</script>

<template>
  <div class="task-stack">
    <section class="task" aria-labelledby="g-modes">
      <h3 id="g-modes" class="task__title">{{ t("learn.modes") }}</h3>
      <div class="opt">
        <label class="opt__label" for="l-learn">{{ t("learn.learn") }}<small>{{ t("learn.learnHint") }}</small></label>
        <ToggleSwitch id="l-learn" v-model="prefs.learn" />
      </div>
      <div class="opt">
        <label class="opt__label" for="l-loop">{{ t("learn.loop") }}<small>{{ t("learn.loopHint") }}</small></label>
        <ToggleSwitch id="l-loop" v-model="prefs.loop" />
      </div>
      <div class="opt">
        <label class="opt__label" for="l-quiz">{{ t("learn.quiz") }}<small>{{ t("learn.quizHint") }}</small></label>
        <ToggleSwitch id="l-quiz" v-model="prefs.quiz" />
      </div>
    </section>

    <section class="task" aria-labelledby="g-words">
      <h3 id="g-words" class="task__title">{{ t("learn.wordsTitle") }}</h3>
      <div v-if="!mine.length" class="empty">
        <PhCursorClick :size="22" />
        <strong>{{ t("learn.emptyTitle") }}</strong>
        <span>{{ t("learn.emptyBody") }}</span>
      </div>
      <ul v-else class="words">
        <li v-for="w in mine" :key="w.id">
          <button type="button" class="word" @click="seekTo(w.t)">
            <span class="w ltr" lang="en">{{ w.word }}</span>
            <span class="m" dir="auto">{{ w.tr }}</span>
            <time class="mono">{{ formatTime(w.t) }}</time>
          </button>
        </li>
      </ul>
      <div class="actions">
        <RouterLink to="/words" class="btn btn--outline btn--sm">{{ t("learn.allWords") }}</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.words {
  list-style: none;
  margin: var(--s-2) 0 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.word {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  align-items: baseline;
  gap: var(--s-3);
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  text-align: start;
}
.word:hover {
  background: var(--surface-2);
}
.w {
  font-weight: 600;
  text-align: start;
}
.m {
  color: var(--text-2);
  font-size: var(--fs-sm);
}
time {
  font-size: 12px;
  color: var(--accent-ink);
}
.empty svg {
  color: var(--accent-ink);
}
</style>
