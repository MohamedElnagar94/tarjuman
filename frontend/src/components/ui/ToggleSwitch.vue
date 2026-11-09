<script setup lang="ts">
defineProps<{ id?: string; label?: string; disabled?: boolean }>();
const model = defineModel<boolean>({ required: true });
</script>

<template>
  <span class="sw">
    <input :id="id" v-model="model" type="checkbox" role="switch" :aria-label="label" :disabled="disabled" />
    <i aria-hidden="true"></i>
  </span>
</template>

<style scoped>
.sw {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 26px;
  flex: none;
}
input {
  position: absolute;
  inset: -9px -2px;
  width: calc(100% + 4px);
  height: calc(100% + 18px);
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
  border-radius: var(--r-pill);
  background: var(--surface-3);
  border: 1px solid var(--line-2);
  transition: background var(--dur) var(--ease), border-color var(--dur) var(--ease);
}
i::after {
  content: "";
  position: absolute;
  top: 3px;
  inset-inline-start: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--text);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform var(--dur) var(--ease), background var(--dur) var(--ease);
}
input:checked + i {
  background: var(--accent);
  border-color: var(--accent-strong);
}
input:checked + i::after {
  background: var(--on-accent);
  transform: translateX(calc(18px * var(--dir)));
}
input:focus-visible + i {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
input:disabled + i {
  opacity: 0.5;
}
</style>
