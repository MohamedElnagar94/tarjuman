<script setup lang="ts">
import { PhX } from "@phosphor-icons/vue";
import { dismiss, toasts } from "@/composables/toast";

function run(id: number, fn: () => void) {
  fn();
  dismiss(id);
}
</script>

<template>
  <div class="host" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in toasts.items" :key="t.id" class="toast" :class="t.tone">
        <span class="text">{{ t.text }}</span>
        <button v-if="t.action" type="button" class="act" @click="run(t.id, t.action.run)">{{ t.action.label }}</button>
        <button type="button" class="x" :aria-label="$t('common.close')" @click="dismiss(t.id)"><PhX :size="14" /></button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.host {
  position: fixed;
  inset-inline: 0;
  bottom: calc(20px + var(--bottom-nav-h));
  z-index: var(--z-toast);
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 0 16px;
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: min(560px, 100%);
  padding: 10px 10px 10px 16px;
  padding-inline-start: 16px;
  border-radius: var(--r-md);
  background: var(--text);
  color: var(--bg);
  box-shadow: var(--shadow-2);
  font-size: var(--fs-sm);
  font-weight: 500;
}
.toast.danger {
  background: var(--danger);
  color: #fff;
}
:root[data-theme="dark"] .toast.danger {
  color: #2a0a0a;
}
.text {
  flex: 1;
}
.act {
  border: 0;
  background: transparent;
  color: inherit;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
  padding: 4px 6px;
}
.x {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: var(--r-xs);
  background: transparent;
  color: inherit;
  opacity: 0.7;
}
.x:hover {
  opacity: 1;
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 200ms var(--ease), transform 200ms var(--ease);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
