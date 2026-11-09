<script setup lang="ts">
defineProps<{ modelValue: string; options: { value: string; label: string }[]; label: string }>();
defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <div class="seg" role="radiogroup" :aria-label="label">
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      role="radio"
      :aria-checked="modelValue === o.value"
      @click="$emit('update:modelValue', o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  padding: 3px;
  gap: 2px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid var(--line);
}
button {
  min-width: 52px;
  min-height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-weight: 600;
  font-size: 12.5px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
button:hover {
  color: var(--text);
}
button[aria-checked="true"] {
  background: var(--lapis-700);
  color: var(--parchment);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 2px 6px rgba(0, 0, 0, 0.25);
}
</style>
