<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import ProgressMeter from "@/components/ui/ProgressMeter.vue";
import { PhArrowsClockwise } from "@phosphor-icons/vue";
import { api } from "@/api/client";
import { cues, loadVideo, retryTranslation, session, sourceCount, tr, translatedCount } from "@/composables/session";
import { isMediaId } from "@/lib/links";
import { toast } from "@/composables/toast";
import { formatTime } from "@/lib/time";

const { t, te, locale } = useI18n();
// An English title on an Arabic page still lines up with the rest of the page.
const align = computed(() => ({ textAlign: locale.value === "ar" ? ("right" as const) : ("left" as const) }));

const langName = (code: string) => (te("langs." + code) ? t("langs." + code) : code);

const source = computed(() => {
  if (session.sameLang) return { tone: "ok", text: t("watch.chip.same", { lang: langName(session.srcLang) }) };
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
/** A file from this computer can be transcribed again, with a more accurate model or other settings. */
const canRedo = computed(() => session.whisper && isMediaId(session.videoId));
const armed = ref(false);
let disarm: number | undefined;
function redoClick() {
  if (!armed.value) {
    armed.value = true;
    window.clearTimeout(disarm);
    disarm = window.setTimeout(() => (armed.value = false), 5000);
    return;
  }
  armed.value = false;
  void redo();
}
async function redo() {
  const link = session.videoId;
  try {
    await api.retranscribe(link.slice(6));
    await loadVideo(link);
  } catch {
    toast(t("errors.UNKNOWN"), { tone: "danger" });
  }
}

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
        <button
          v-if="canRedo"
          type="button"
          class="redo"
          :class="{ armed }"
          :title="t('watch.redo.hint')"
          @click="redoClick"
        >
          <PhArrowsClockwise :size="14" />
          {{ armed ? t("watch.redo.confirm") : t("watch.redo.label") }}
        </button>
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
.redo {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border-radius: var(--r-pill);
  border: 1px dashed var(--line-strong, var(--line));
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: var(--fs-xs);
  cursor: pointer;
}
.redo:hover {
  background: var(--surface-2);
}
.redo.armed {
  border-style: solid;
  border-color: var(--accent);
  color: var(--accent-ink);
}
.redo:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
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
