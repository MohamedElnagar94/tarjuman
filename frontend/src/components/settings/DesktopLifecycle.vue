<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api, type DesktopSettings } from "@/api/client";
import { toast } from "@/composables/toast";

const { t } = useI18n();
const KEYS = ["minimizeToTray", "closeToTray", "startWithWindows", "keepEngine"] as const;

const settings = ref<DesktopSettings | null>(null);
const available = ref(false);
const supported = ref(true);
const remote = ref(false);
const saving = ref("");

async function load() {
  try {
    const r = await api.desktop();
    settings.value = r.settings;
    available.value = r.available;
    supported.value = r.supported;
  } catch {
    remote.value = true; // managed from the computer only
  }
}

async function set(key: (typeof KEYS)[number], on: boolean) {
  if (!settings.value) return;
  const before = settings.value[key];
  settings.value[key] = on;
  saving.value = key;
  try {
    const r = await api.setDesktop({ [key]: on });
    settings.value = r.settings;
  } catch {
    settings.value[key] = before;
    toast(t("errors.UNKNOWN"), { tone: "danger" });
  } finally {
    saving.value = "";
  }
}

onMounted(load);
</script>

<template>
  <div>
    <p class="panel__lead">{{ t("desktop.lead") }}</p>
    <p v-if="remote" class="muted">{{ t("phone.remote") }}</p>
    <p v-else-if="!supported" class="muted">{{ t("desktop.windowsOnly") }}</p>
    <template v-else-if="settings">
      <p v-if="!available" class="note">
        {{ t("desktop.notApp") }}
        <code dir="ltr" class="mono">python -m tarjuman app</code>
      </p>
      <div v-for="k in KEYS" :key="k" class="opt">
        <label class="opt__label" :for="'dk-' + k">
          {{ t(`desktop.${k}`) }}
          <small>{{ t(`desktop.${k}Hint`) }}</small>
        </label>
        <ToggleSwitch :id="'dk-' + k" :model-value="settings[k]" :disabled="saving === k" @update:model-value="set(k, $event)" />
      </div>
      <p class="muted small">{{ t("desktop.extensionNeedsEngine") }}</p>
    </template>
  </div>
</template>

<style scoped>
.note {
  margin: var(--s-3) 0;
  padding: var(--s-2) var(--s-3);
  border-radius: var(--r-md);
  background: var(--surface-2);
  border: 1px solid var(--line);
  font-size: var(--fs-sm);
}
.note code {
  display: inline-block;
  padding: 0 6px;
  border-radius: var(--r-xs);
  background: var(--surface-3);
}
.small {
  font-size: var(--fs-sm);
  margin-top: var(--s-3);
}
</style>
