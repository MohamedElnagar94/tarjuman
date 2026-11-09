<script setup lang="ts">
import { SIZE_MIN, SIZE_MAX } from "@/shared/settings";
import { t } from "@/shared/i18n";

const props = defineProps<{ modelValue: number }>();
const emit = defineEmits<{ "update:modelValue": [value: number] }>();
const step = (d: number) => emit("update:modelValue", Math.min(SIZE_MAX, Math.max(SIZE_MIN, props.modelValue + d)));
</script>

<template>
  <div class="step" role="group" :aria-label="t('lblSize')">
    <button type="button" :aria-label="t('tbSmaller')" :disabled="modelValue <= SIZE_MIN" @click="step(-2)">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14" /></svg>
    </button>
    <output aria-live="polite">{{ modelValue }}</output>
    <button type="button" :aria-label="t('tbLarger')" :disabled="modelValue >= SIZE_MAX" @click="step(2)">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M5 12h14M12 5v14" /></svg>
    </button>
  </div>
</template>

<style scoped>
.step {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid var(--line);
}
button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 28px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
}
button:hover:not(:disabled) {
  background: var(--surface-3);
}
button:disabled {
  opacity: 0.35;
  cursor: default;
}
output {
  min-width: 28px;
  text-align: center;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
