<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhCheckCircle, PhLockSimple, PhWarningCircle } from "@phosphor-icons/vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api, errorCode } from "@/api/client";
import type { AiProvider, AiSettings, AiSettingsInput, AiStyle } from "@/api/types";
import { errText } from "@/i18n";
import { useHealth } from "@/composables/health";

const { t } = useI18n();
const { refresh: refreshHealth } = useHealth();

const PRESETS = [
  { id: "gemini", base: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash", free: true },
  { id: "groq", base: "https://api.groq.com/openai/v1", model: "llama-3.3-70b-versatile", free: true },
  { id: "openrouter", base: "https://openrouter.ai/api/v1", model: "", free: false },
  { id: "ollama", base: "http://localhost:11434/v1", model: "qwen2.5:7b", free: false },
] as const;

const state = ref<"loading" | "ready" | "local-only" | "down">("loading");
const saved = ref<AiSettings | null>(null);
const form = reactive({ enabled: false, provider: "anthropic" as AiProvider, style: "msa" as AiStyle, model: "", baseUrl: "" });
/** Typed key; never pre-filled, never read back from the server. */
const key = ref("");
const clearKey = ref(false);
const busy = ref<"" | "save" | "test">("");
const result = ref<{ ok: boolean; text: string } | null>(null);

function fill(s: AiSettings) {
  saved.value = s;
  Object.assign(form, { enabled: s.enabled, provider: s.provider, style: s.style, model: s.model || "", baseUrl: s.baseUrl || "" });
  key.value = "";
  clearKey.value = false;
}

onMounted(async () => {
  try {
    fill((await api.settings()).ai);
    state.value = "ready";
  } catch (e) {
    state.value = errorCode(e) === "LOCAL_ONLY" ? "local-only" : "down";
  }
});

const claude = computed(() => form.provider === "anthropic");
/** The server drops a stored key when the provider or server address changes (specs §3.5). */
const keyWillReset = computed(
  () => !!saved.value?.hasKey && (form.provider !== saved.value.provider || (form.baseUrl || "") !== (saved.value.baseUrl || "")),
);
const keyPlaceholder = computed(() => {
  if (saved.value?.hasKey && !keyWillReset.value && !clearKey.value) return t("ai.key.saved", { hint: saved.value.keyHint });
  return claude.value ? "sk-ant-…" : t("ai.key.optional");
});

const providerOptions = computed(() => [
  { value: "anthropic" as AiProvider, label: "Claude" },
  { value: "openai" as AiProvider, label: t("ai.provider.other") },
]);
const styleOptions = computed(() => [
  { value: "msa" as AiStyle, label: t("ai.style.msa") },
  { value: "egyptian" as AiStyle, label: t("ai.style.egyptian") },
]);

function setProvider(p: AiProvider) {
  if (p === form.provider) return;
  form.provider = p;
  form.model = "";
  form.baseUrl = "";
}

function usePreset(p: (typeof PRESETS)[number]) {
  form.baseUrl = p.base;
  form.model = p.model;
}

async function save(): Promise<boolean> {
  busy.value = "save";
  result.value = null;
  const body: AiSettingsInput = { ...form, model: form.model.trim(), baseUrl: form.baseUrl.trim() };
  if (key.value.trim()) body.apiKey = key.value.trim();
  else if (clearKey.value) body.apiKey = null;
  try {
    const r = await api.saveSettings(body);
    fill(r.ai);
    void refreshHealth();
    if (r.ai.enabled && !r.ai.ready) result.value = { ok: false, text: claude.value ? t("ai.saved.needKey") : t("ai.saved.needServer") };
    else result.value = { ok: true, text: r.ai.enabled ? t("ai.saved.on") : t("ai.saved.off") };
    return true;
  } catch (e) {
    result.value = { ok: false, text: errText(errorCode(e), (e as Error).message) };
    return false;
  } finally {
    busy.value = "";
  }
}

async function test() {
  if (!(await save())) return;
  busy.value = "test";
  result.value = { ok: true, text: t("ai.testing") };
  try {
    const r = await api.testAi();
    result.value = { ok: true, text: t("ai.testOk", { text: r.text, secs: (r.ms / 1000).toFixed(1), model: r.model }) };
  } catch (e) {
    result.value = { ok: false, text: errText(errorCode(e), (e as Error).message) };
  } finally {
    busy.value = "";
  }
}
</script>

<template>
  <div class="ai">
    <p class="lead">{{ t("ai.lead") }}</p>

    <div v-if="state === 'loading'" class="skeleton" style="height: 220px"></div>
    <div v-else-if="state === 'local-only'" class="notice notice--accent">
      <PhLockSimple :size="18" />
      <div class="notice__body">
        <strong>{{ t("ai.localOnly.title") }}</strong>
        <span>{{ t("ai.localOnly.body") }}</span>
      </div>
    </div>
    <p v-else-if="state === 'down'" class="notice notice--danger"><PhWarningCircle :size="18" />{{ errText("NO_SERVER") }}</p>

    <form v-else class="form" @submit.prevent="save">
      <div class="opt">
        <label class="opt__label" for="ai-on">{{ t("ai.enabled") }}<small>{{ t("ai.enabledHint") }}</small></label>
        <ToggleSwitch id="ai-on" v-model="form.enabled" />
      </div>
      <div class="opt">
        <span class="opt__label">{{ t("ai.style.label") }}</span>
        <SegmentedControl v-model="form.style" :options="styleOptions" :label="t('ai.style.label')" size="sm" />
      </div>
      <div class="opt">
        <span class="opt__label">{{ t("ai.provider.label") }}</span>
        <SegmentedControl :model-value="form.provider" :options="providerOptions" :label="t('ai.provider.label')" size="sm" @update:model-value="setProvider" />
      </div>

      <div v-if="!claude" class="field">
        <label for="ai-base">{{ t("ai.base.label") }}</label>
        <input id="ai-base" v-model="form.baseUrl" class="input ltr" type="url" placeholder="https://…/v1" autocomplete="off" spellcheck="false" />
        <div class="presets" role="group" :aria-label="t('ai.base.presets')">
          <button v-for="p in PRESETS" :key="p.id" type="button" class="btn btn--outline btn--sm" :aria-pressed="form.baseUrl === p.base" @click="usePreset(p)">
            {{ t("ai.preset." + p.id) }}<span v-if="p.free" class="free">{{ t("ai.preset.free") }}</span>
          </button>
        </div>
      </div>

      <div class="field">
        <label for="ai-key">{{ t("ai.key.label") }}</label>
        <input id="ai-key" v-model="key" class="input ltr" type="password" autocomplete="new-password" spellcheck="false" :placeholder="keyPlaceholder" />
        <span class="field__help">{{ claude ? t("ai.key.helpClaude") : t("ai.key.helpOther") }}</span>
        <span v-if="keyWillReset" class="field__error">{{ t("ai.key.willReset") }}</span>
        <label v-else-if="saved?.hasKey" class="check">
          <input v-model="clearKey" type="checkbox" />
          <span>{{ t("ai.key.clear") }}</span>
        </label>
      </div>

      <div class="field">
        <label for="ai-model">{{ t("ai.model.label") }}</label>
        <input id="ai-model" v-model="form.model" class="input ltr" type="text" autocomplete="off" spellcheck="false" :placeholder="claude ? saved?.defaultModel || 'claude-opus-5-5' : t('ai.model.placeholder')" />
        <span class="field__help">{{ claude ? t("ai.model.helpClaude", { model: saved?.defaultModel || "claude-opus-5-5" }) : t("ai.model.helpOther") }}</span>
      </div>

      <div class="actions">
        <button class="btn btn--primary" type="submit" :disabled="!!busy">{{ busy === "save" ? t("common.saving") : t("common.save") }}</button>
        <button class="btn btn--outline" type="button" :disabled="!!busy" @click="test">{{ busy === "test" ? t("ai.testing") : t("ai.test") }}</button>
      </div>
      <p v-if="result" class="notice" :class="result.ok ? '' : 'notice--danger'" role="status">
        <PhCheckCircle v-if="result.ok" :size="18" class="ok" />
        <PhWarningCircle v-else :size="18" />
        <span>{{ result.text }}</span>
      </p>
    </form>
  </div>
</template>

<style scoped>
.lead {
  color: var(--text-2);
  font-size: var(--fs-sm);
  max-width: 62ch;
  margin-bottom: var(--s-4);
}
.form {
  display: grid;
  gap: var(--s-4);
}
.form .opt + .field,
.form .opt {
  margin: 0;
}
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.presets [aria-pressed="true"] {
  border-color: var(--accent-line);
  background: var(--accent-soft);
}
.free {
  margin-inline-start: 6px;
  font-size: 11px;
  color: var(--ok);
}
.check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-xs);
  color: var(--text-2);
  cursor: pointer;
}
.check input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-strong);
}
.ok {
  color: var(--ok);
}
.actions {
  margin-top: 0;
}
</style>
