<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhPlus, PhSpeakerHigh, PhWarningCircle, PhX } from "@phosphor-icons/vue";
import { api, errorCode } from "@/api/client";
import type { PronounceRule } from "@/api/types";
import { errText } from "@/i18n";
import { usePrefs } from "@/composables/prefs";
import { toast } from "@/composables/toast";
import { liveVoiceId, playTts } from "@/composables/voices";

const { t } = useI18n();
const prefs = usePrefs();
let seq = 0;
type Row = PronounceRule & { key: number };
const rows = ref<Row[]>([]);
const state = ref<"loading" | "ready" | "down">("loading");
const busy = ref(false);
const sample = ref("");
const heard = ref("");
const listening = ref(false);

const row = (r: PronounceRule = { from: "", to: "" }): Row => ({ ...r, key: ++seq });

onMounted(async () => {
  try {
    rows.value = ((await api.pronounce()).items || []).map(row);
    state.value = "ready";
  } catch {
    state.value = "down";
  }
  if (!rows.value.length) rows.value.push(row());
});

const items = () => rows.value.map((r) => ({ from: r.from.trim(), to: r.to.trim() })).filter((r) => r.from && r.to);

async function add() {
  rows.value.push(row());
  await Promise.resolve();
  const inputs = document.querySelectorAll<HTMLInputElement>(".dict .from");
  inputs[inputs.length - 1]?.focus();
}

async function save(quiet = false): Promise<boolean> {
  busy.value = true;
  try {
    await api.savePronounce(items());
    if (!quiet) toast(t("pronounce.saved"), { tone: "ok" });
    return true;
  } catch (e) {
    toast(errText(errorCode(e)), { tone: "danger" });
    return false;
  } finally {
    busy.value = false;
  }
}

/** Saves first, like the prototype: the preview and the voice use the stored dictionary. */
async function listen() {
  const text = sample.value.trim();
  if (!text) return;
  listening.value = true;
  try {
    if (!(await save(true))) return;
    heard.value = (await api.previewPronounce(text)).text;
    await playTts(text, prefs.tl, liveVoiceId(prefs.voice));
  } catch (e) {
    toast(errText(errorCode(e)), { tone: "danger" });
  } finally {
    listening.value = false;
  }
}
</script>

<template>
  <div class="dict">
    <p class="lead">{{ t("pronounce.lead") }}</p>
    <p v-if="state === 'down'" class="notice notice--danger"><PhWarningCircle :size="18" />{{ errText("NO_SERVER") }}</p>
    <div v-else-if="state === 'loading'" class="skeleton" style="height: 96px"></div>
    <template v-else>
      <div class="head" aria-hidden="true">
        <span>{{ t("pronounce.word") }}</span>
        <span></span>
        <span>{{ t("pronounce.say") }}</span>
      </div>
      <ul class="rows">
        <li v-for="(r, i) in rows" :key="r.key" class="row">
          <input v-model="r.from" class="input from" dir="auto" :aria-label="t('pronounce.wordN', { n: i + 1 })" :placeholder="t('pronounce.wordPh')" />
          <span class="arrow" aria-hidden="true">{{ prefs.uiLang === "ar" ? "←" : "→" }}</span>
          <input v-model="r.to" class="input" dir="auto" :aria-label="t('pronounce.sayN', { n: i + 1 })" :placeholder="t('pronounce.sayPh')" />
          <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('pronounce.remove', { n: i + 1 })" @click="rows.splice(i, 1)"><PhX :size="15" /></button>
        </li>
      </ul>
      <div class="actions">
        <button type="button" class="btn btn--outline btn--sm" @click="add"><PhPlus :size="15" />{{ t("pronounce.add") }}</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="busy" @click="save()">{{ t("common.save") }}</button>
      </div>

      <div class="try field">
        <label for="dict-try">{{ t("pronounce.try") }}</label>
        <div class="try__row">
          <input id="dict-try" v-model="sample" class="input" dir="auto" :placeholder="t('pronounce.tryPh')" @keydown.enter.prevent="listen" />
          <button type="button" class="btn btn--outline" :disabled="listening || !sample.trim()" @click="listen"><PhSpeakerHigh :size="16" />{{ t("pronounce.listen") }}</button>
        </div>
        <span v-if="heard" class="field__help" dir="auto">{{ t("pronounce.heard", { text: heard }) }}</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.lead {
  color: var(--text-2);
  font-size: var(--fs-sm);
  max-width: 62ch;
  margin-bottom: var(--s-4);
}
.head,
.row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20px minmax(0, 1fr) 34px;
  gap: var(--s-2);
  align-items: center;
}
.head {
  font-size: var(--fs-xs);
  color: var(--text-2);
  margin-bottom: 6px;
}
.rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.arrow {
  color: var(--text-3);
  text-align: center;
}
.try {
  margin-top: var(--s-6);
  padding-top: var(--s-5);
  border-top: 1px solid var(--line);
}
.try__row {
  display: flex;
  gap: var(--s-2);
}
@media (max-width: 480px) {
  .try__row {
    flex-direction: column;
  }
}
</style>
