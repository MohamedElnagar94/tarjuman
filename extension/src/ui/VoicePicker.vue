<script setup lang="ts">
import { t } from "@/shared/i18n";
import type { Voice } from "./useExtension";

defineProps<{ modelValue: string; voices: Voice[]; previewing: boolean; id?: string }>();
defineEmits<{ "update:modelValue": [value: string]; preview: [] }>();
</script>

<template>
  <span class="pick">
    <select
      :id="id"
      class="select"
      :value="modelValue"
      :disabled="!voices.length"
      @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-if="!voices.length" value="">{{ t("voiceDefault") }}</option>
      <option v-for="(v, i) in voices" :key="v.id" :value="i === 0 ? '' : v.id">{{ v.name }} — {{ v.accent }}</option>
    </select>
    <button
      type="button"
      class="play"
      :class="{ busy: previewing }"
      :disabled="previewing"
      :aria-label="t('btnPreviewVoice')"
      :title="t('btnPreviewVoice')"
      @click="$emit('preview')"
    >
      <svg v-if="!previewing" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l11-6.5a1 1 0 0 0 0-1.72l-11-6.5A1 1 0 0 0 8 5.5Z" /></svg>
      <span v-else class="spin" aria-hidden="true"></span>
    </button>
  </span>
</template>

<style scoped>
.pick {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.select {
  max-width: 172px;
  min-width: 0;
  text-overflow: ellipsis;
}
.play {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 50%;
  border: 1px solid rgba(255, 210, 122, 0.35);
  background: rgba(255, 210, 122, 0.1);
  color: var(--saffron-300);
  cursor: pointer;
  transition: background 0.15s;
}
.play:hover {
  background: rgba(255, 210, 122, 0.2);
}
[dir="rtl"] .play svg {
  transform: none;
}
.spin {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 210, 122, 0.3);
  border-top-color: var(--saffron-300);
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
