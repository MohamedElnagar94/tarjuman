<script setup lang="ts">
import { ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhArrowBendDownLeft, PhListBullets, PhSparkle, PhWarningCircle } from "@phosphor-icons/vue";
import { api, errorCode } from "@/api/client";
import type { Answer, Summary } from "@/api/types";
import { errText } from "@/i18n";
import { seekTo, session, useAiChapters } from "@/composables/session";
import { formatTime } from "@/lib/time";

const { t } = useI18n();
const summary = ref<Summary | null>(null);
const sumBusy = ref(false);
const sumErr = ref("");
const question = ref("");
const answer = ref<(Answer & { q: string }) | null>(null);
const askBusy = ref(false);
const askErr = ref("");
const needsSetup = ref(false);

watch(
  () => session.videoId,
  () => {
    summary.value = null;
    answer.value = null;
    question.value = "";
    sumErr.value = askErr.value = "";
  },
);

function fail(e: unknown, into: typeof sumErr) {
  const code = errorCode(e);
  if (code === "AI_NOT_READY") needsSetup.value = true;
  else into.value = errText(code, (e as Error).message);
}

async function summarize() {
  sumBusy.value = true;
  sumErr.value = "";
  try {
    summary.value = await api.summary(session.link, session.tl);
    // A video whose owner listed no chapters gets these in the transcript and on the timeline.
    useAiChapters(summary.value.chapters);
    needsSetup.value = false;
  } catch (e) {
    fail(e, sumErr);
  } finally {
    sumBusy.value = false;
  }
}

async function ask() {
  const q = question.value.trim();
  if (!q) return;
  askBusy.value = true;
  askErr.value = "";
  try {
    answer.value = { ...(await api.ask(session.link, session.tl, q)), q };
    needsSetup.value = false;
  } catch (e) {
    fail(e, askErr);
  } finally {
    askBusy.value = false;
  }
}

const dir = () => (session.tl === "ar" ? "rtl" : "ltr");
</script>

<template>
  <div class="task-stack">
    <div v-if="needsSetup" class="notice notice--accent" role="alert">
      <PhSparkle :size="18" />
      <div class="notice__body">
        <strong>{{ t("ask.setup.title") }}</strong>
        <span>{{ t("ask.setup.body") }}</span>
        <RouterLink to="/settings#ai" class="btn btn--primary btn--sm setup">{{ t("ask.setup.cta") }}</RouterLink>
      </div>
    </div>

    <section class="task" aria-labelledby="g-sum">
      <h3 id="g-sum" class="task__title">{{ t("ask.summary.title") }}</h3>
      <p class="task__lead">{{ t("ask.summary.lead") }}</p>
      <div v-if="!summary" class="actions">
        <button type="button" class="btn btn--primary" :disabled="sumBusy || !session.link" @click="summarize">
          <PhListBullets :size="18" />
          {{ sumBusy ? t("ask.summary.busy") : t("ask.summary.start") }}
        </button>
      </div>
      <div v-if="sumBusy" class="sk" aria-hidden="true">
        <div class="skeleton" style="height: 14px; width: 92%"></div>
        <div class="skeleton" style="height: 14px; width: 80%"></div>
        <div class="skeleton" style="height: 14px; width: 64%"></div>
      </div>
      <p v-if="sumErr" class="notice notice--danger" role="alert"><PhWarningCircle :size="18" />{{ sumErr }}</p>
      <div v-if="summary" class="sum" :dir="dir()">
        <p class="sum__text">{{ summary.summary }}</p>
        <ul v-if="summary.points.length" class="sum__points">
          <li v-for="(p, i) in summary.points" :key="i">{{ p }}</li>
        </ul>
        <template v-if="summary.chapters.length">
          <h4 class="sum__h">{{ t("ask.summary.chapters") }}</h4>
          <ol class="chapters">
            <li v-for="(c, i) in summary.chapters" :key="i">
              <button type="button" class="moment" @click="seekTo(c.start)">
                <time class="mono">{{ formatTime(c.start) }}</time>
                <span>{{ c.title }}</span>
              </button>
            </li>
          </ol>
        </template>
      </div>
    </section>

    <section class="task" aria-labelledby="g-ask">
      <h3 id="g-ask" class="task__title">{{ t("ask.ask.title") }}</h3>
      <form class="ask" @submit.prevent="ask">
        <label class="sr-only" for="ask-q">{{ t("ask.ask.label") }}</label>
        <input id="ask-q" v-model="question" class="input" type="text" :placeholder="t('ask.ask.placeholder')" autocomplete="off" :disabled="askBusy" />
        <button type="submit" class="btn btn--primary" :disabled="askBusy || !question.trim()">
          <PhArrowBendDownLeft :size="16" />{{ askBusy ? t("ask.ask.busy") : t("ask.ask.send") }}
        </button>
      </form>
      <p v-if="askErr" class="notice notice--danger" role="alert"><PhWarningCircle :size="18" />{{ askErr }}</p>
      <div v-if="answer" class="answer">
        <p class="answer__q">{{ answer.q }}</p>
        <p class="answer__a" :dir="dir()">{{ answer.answer }}</p>
        <div v-if="answer.moments.length" class="moments">
          <button v-for="m in answer.moments" :key="m" type="button" class="moment pill" @click="seekTo(m)">
            <time class="mono">{{ formatTime(m) }}</time>
            <span>{{ t("ask.ask.goTo") }}</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.setup {
  justify-self: start;
}
.sk {
  display: grid;
  gap: 8px;
  margin-top: var(--s-3);
}
.notice {
  margin-top: var(--s-3);
}
.sum {
  margin-top: var(--s-3);
  display: grid;
  gap: var(--s-3);
}
.sum__text {
  font-size: var(--fs-md);
  line-height: 1.85;
}
.sum__points {
  margin: 0;
  padding-inline-start: 20px;
  color: var(--text-2);
  font-size: var(--fs-sm);
  display: grid;
  gap: 4px;
}
.sum__h {
  font-size: var(--fs-sm);
  font-weight: 600;
  margin-top: var(--s-2);
}
.chapters {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.moment {
  display: flex;
  align-items: baseline;
  gap: 12px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--r-sm);
  background: transparent;
  color: var(--text);
  text-align: start;
  font-size: var(--fs-sm);
}
.moment:hover {
  background: var(--surface-2);
}
.moment time {
  color: var(--accent-ink);
  font-size: 12px;
  min-width: 46px;
  direction: ltr;
}
.ask {
  display: flex;
  gap: var(--s-2);
  margin-top: var(--s-2);
}
.answer {
  margin-top: var(--s-4);
  padding: var(--s-4);
  border-radius: var(--r-md);
  background: var(--bg);
  border: 1px solid var(--line);
  display: grid;
  gap: var(--s-2);
}
.answer__q {
  font-size: var(--fs-xs);
  color: var(--text-2);
}
.answer__a {
  line-height: 1.85;
}
.moments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.moment.pill {
  width: auto;
  border: 1px solid var(--line-2);
  border-radius: var(--r-pill);
  padding: 4px 12px;
  gap: 8px;
}
.moment.pill time {
  min-width: 0;
}
@media (max-width: 480px) {
  .ask {
    flex-direction: column;
  }
}
</style>
