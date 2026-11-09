<script setup lang="ts">
defineProps<{ modelValue: boolean; id?: string; disabled?: boolean; label?: string }>();
defineEmits<{ "update:modelValue": [value: boolean] }>();
</script>

<template>
  <span class="switch">
    <input
      :id="id"
      type="checkbox"
      role="switch"
      :checked="modelValue"
      :disabled="disabled"
      :aria-label="label"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <i aria-hidden="true"></i>
  </span>
</template>

<style scoped>
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 24px;
  flex: none;
}
input {
  position: absolute;
  inset: -6px;
  width: calc(100% + 12px);
  height: calc(100% + 12px);
  margin: 0;
  opacity: 0;
  cursor: pointer;
  z-index: 1;
}
input:disabled {
  cursor: not-allowed;
}
i {
  position: absolute;
  inset: 0;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  transition: background 0.18s var(--ease);
  pointer-events: none;
}
i::after {
  content: "";
  position: absolute;
  top: 3px;
  inset-inline-start: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--parchment);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
  transition: transform 0.18s var(--ease), background 0.18s;
}
input:checked + i {
  background: linear-gradient(180deg, #FFDE9A, #FFC35A);
}
input:checked + i::after {
  transform: translateX(16px);
  background: var(--lapis-900);
}
[dir="rtl"] input:checked + i::after {
  transform: translateX(-16px);
}
input:focus-visible + i {
  box-shadow: var(--ring);
}
input:disabled + i {
  opacity: 0.45;
}
</style>
