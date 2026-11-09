<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhArrowSquareOut, PhExport, PhMagnifyingGlass, PhSpeakerHigh, PhWarningCircle } from "@phosphor-icons/vue";
import ConfirmButton from "@/components/ui/ConfirmButton.vue";
import { api, errorCode } from "@/api/client";
import type { VocabItem } from "@/api/types";
import { errText } from "@/i18n";
import { toast } from "@/composables/toast";
import { playTts } from "@/composables/voices";
import { linkFor } from "@/lib/links";
import { formatTime } from "@/lib/time";

const { t } = useI18n();
const items = ref<VocabItem[] | null>(null);
const failed = ref(false);
const q = ref("");

onMounted(async () => {
  try {
    items.value = (await api.vocab()).items || [];
  } catch {
    items.value = [];
    failed.value = true;
  }
  document.title = t("words.title") + " | " + t("app.name");
});

const shown = computed(() => {
  const list = [...(items.value || [])].sort((a, b) => (b.at || 0) - (a.at || 0));
  const s = q.value.trim().toLowerCase();
  if (!s) return list;
  return list.filter((x) => [x.word, x.tr, x.sentence, x.title].some((v) => String(v || "").toLowerCase().includes(s)));
});

async function remove(x: VocabItem) {
  try {
    await api.deleteVocab(x.id);
    items.value = (items.value || []).filter((i) => i.id !== x.id);
  } catch (e) {
    toast(errText(errorCode(e)), { tone: "danger" });
  }
}

async function listen(x: VocabItem) {
  try {
    await playTts(x.word, "en");
  } catch {
    toast(t("lookup.noAudio"), { tone: "danger" });
  }
}
</script>

<template>
  <div class="page words">
    <header class="page__head head">
      <div>
        <h1 class="page__title">{{ t("words.title") }}</h1>
        <p class="muted">{{ t("words.lead") }}</p>
      </div>
      <a class="btn btn--outline" :href="api.vocabCsvUrl" download :aria-disabled="!items?.length"><PhExport :size="18" />{{ t("words.export") }}</a>
    </header>

    <p v-if="failed" class="notice notice--danger" role="alert"><PhWarningCircle :size="18" />{{ errText("NO_SERVER") }}</p>

    <div v-if="items && items.length" class="tools">
      <div class="search">
        <PhMagnifyingGlass :size="16" aria-hidden="true" />
        <label class="sr-only" for="wq">{{ t("words.search") }}</label>
        <input id="wq" v-model="q" type="search" :placeholder="t('words.search')" autocomplete="off" />
      </div>
      <span class="muted count">{{ t("words.count", { n: shown.length }) }}</span>
    </div>

    <div v-if="items === null" class="grid" aria-busy="true">
      <div v-for="n in 6" :key="n" class="skeleton sk"></div>
    </div>
    <div v-else-if="!items.length" class="empty big">
      <strong>{{ t("words.emptyTitle") }}</strong>
      <span>{{ t("words.emptyBody") }}</span>
      <RouterLink to="/" class="btn btn--primary btn--sm">{{ t("words.emptyCta") }}</RouterLink>
    </div>
    <p v-else-if="!shown.length" class="muted">{{ t("words.noMatch") }}</p>

    <ul v-else class="grid">
      <li v-for="x in shown" :key="x.id" class="card">
        <div class="card__top">
          <span class="word ltr" lang="en">{{ x.word }}</span>
          <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('lookup.listen')" @click="listen(x)"><PhSpeakerHigh :size="16" /></button>
        </div>
        <p class="meaning" dir="auto">{{ x.tr || "…" }}</p>
        <blockquote v-if="x.sentence" class="ctx">
          <p class="ltr" lang="en">{{ x.sentence }}</p>
          <p v-if="x.sentenceTr" class="ctx__tr" dir="auto">{{ x.sentenceTr }}</p>
        </blockquote>
        <div class="card__foot">
          <RouterLink v-if="x.videoId" class="go" :to="{ name: 'watch', query: { url: linkFor(x.videoId), t: String(Math.floor(x.t || 0)) } }">
            <PhArrowSquareOut :size="15" />
            <span class="go__title" dir="auto">{{ x.title || t("words.video") }}</span>
            <span class="mono">{{ formatTime(x.t || 0) }}</span>
          </RouterLink>
          <ConfirmButton icon :label="t('common.delete')" :confirm-label="t('common.confirmDelete')" @confirm="remove(x)" />
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--s-4);
  flex-wrap: wrap;
}
.tools {
  display: flex;
  align-items: center;
  gap: var(--s-4);
  margin-bottom: var(--s-5);
}
.search {
  flex: 1;
  max-width: 420px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-inline: 12px;
  min-height: 40px;
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  background: var(--surface-1);
  color: var(--text-3);
}
.search:focus-within {
  border-color: var(--accent-line);
}
.search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  min-height: 38px;
}
.count {
  font-size: var(--fs-xs);
}
.grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--s-4);
}
.sk {
  height: 180px;
  border-radius: var(--r-lg);
}
.card {
  display: flex;
  flex-direction: column;
  gap: var(--s-2);
  padding: var(--s-4) var(--s-5);
  border-radius: var(--r-lg);
  background: var(--surface-1);
  border: 1px solid var(--line);
}
.card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.word {
  font-size: var(--fs-xl);
  font-weight: 600;
}
.meaning {
  font-size: var(--fs-lg);
  color: var(--accent-ink);
  font-weight: 500;
}
.ctx {
  margin: 0;
  padding-inline-start: var(--s-3);
  border-inline-start: 2px solid var(--line-2);
  display: grid;
  gap: 2px;
  font-size: var(--fs-xs);
  color: var(--text-2);
}
.ctx .ltr {
  text-align: left;
}
.card__foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-2);
  padding-top: var(--s-2);
  border-top: 1px solid var(--line);
}
.go {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  min-height: 34px;
  color: var(--text-2);
  font-size: var(--fs-xs);
  text-decoration: none;
  border-radius: var(--r-xs);
}
.go:hover {
  color: var(--text);
}
.go__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.go .mono {
  color: var(--accent-ink);
  flex: none;
}
.empty.big {
  max-width: 560px;
}
@media (max-width: 480px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
