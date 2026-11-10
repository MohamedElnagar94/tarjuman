<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import ProgressMeter from "@/components/ui/ProgressMeter.vue";
import { cues, retryTranslation, session, sourceCount, tr, translatedCount } from "@/composables/session";
import { formatTime } from "@/lib/time";

const { t, te, locale } = useI18n();
// An English title on an Arabic page still lines up with the rest of the page.
const align = computed(() => ({ textAlign: locale.value === "ar" ? ("right" as const) : ("left" as const) }));

const langName = (code: string) => (te("langs." + code) ? t("langs." + code) : code);

const source = computed(() => {
  if (session.already) return session.autoTranslated ? { tone: "accent", text: t("watch.chip.ytAuto") } : { tone: "ok", text: t("watch.chip.ytHuman") };
  if (session.whisper) return { tone: "accent", text: t("watch.chip.whisper") };
  if (session.asr) return { tone: "accent", text: t("watch.chip.asr") };
  return { tone: "accent", text: t("watch.chip.machine", { lang: langName(session.srcLang) }) };
});

// Progress of the lines around the playhead: only that window is translated (see session.ts), so a
// whole-video percentage would sit near 0% on a long video even when everything you watch is ready.
const windowLines = computed(() => {
  const t = session.time;
  const out: number[] = [];
  cues.value.forEach((c, i) => {
    if (c.src && c.start <= t + 300 && c.end >= t - 30) out.push(i);
  });
  return out;
});
const pct = computed(() => {
  const w = windowLines.value;
  if (!w.length) return sourceCount.value ? Math.round((translatedCount.value / sourceCount.value) * 100) : 100;
  return Math.round((w.filter((i) => tr.value[i]).length / w.length) * 100);
});
const showMeter = computed(
  () => !session.already && sourceCount.value > 0 && (pct.value < 100 || (!session.translating && session.translateFailed > 0)),
);
</script>

<template>
  <div class="meta">
    <div class="info">
      <h1 class="title" dir="auto" :style="align">{{ session.title || " " }}</h1>
      <p v-if="session.author" class="by" dir="auto" :style="align">{{ session.author }}</p>
      <div class="chips">
        <span class="chip" :class="'chip--' + source.tone">{{ source.text }}</span>
        <span class="chip">{{ t("watch.chip.lines", { n: cues.length }) }}</span>
        <span v-if="session.lengthSeconds" class="chip mono">{{ formatTime(session.lengthSeconds) }}</span>
      </div>
    </div>
    <div v-if="showMeter" class="progress" aria-live="polite">
      <ProgressMeter
        :value="pct"
        :label="session.translating ? t('watch.translate.progress', { pct }) : t('watch.translate.missing', { n: session.translateFailed })"
      />
      <button v-if="!session.translating && session.translateFailed" class="btn btn--quiet btn--sm" type="button" @click="retryTranslation">{{ t("common.retry") }}</button>
    </div>
  </div>
</template>

<style scoped>
.meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s-6);
  padding: var(--s-2) 0 var(--s-4);
}
.info {
  min-width: 0;
}
.title {
  font-size: var(--fs-xl);
  font-weight: 600;
  line-height: 1.45;
}
.by {
  color: var(--text-2);
  font-size: var(--fs-sm);
  margin-top: 2px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: var(--s-3);
}
.progress {
  flex: none;
  width: 240px;
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding-top: 8px;
}
@media (max-width: 759px) {
  .meta {
    flex-direction: column;
    gap: var(--s-3);
    padding: var(--s-3) var(--s-4) var(--s-4);
  }
  .title {
    font-size: var(--fs-lg);
  }
  .progress {
    width: 100%;
  }
}
</style>
