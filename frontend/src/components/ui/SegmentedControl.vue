<script setup lang="ts" generic="T extends string | number">
defineProps<{ options: { value: T; label: string; title?: string }[]; label: string; size?: "sm" | "md"; block?: boolean }>();
const model = defineModel<T>({ required: true });

function onKey(e: KeyboardEvent, options: { value: T }[]) {
  const keys = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"];
  if (!keys.includes(e.key)) return;
  e.preventDefault();
  const rtl = getComputedStyle(e.currentTarget as Element).direction === "rtl";
  const forward = e.key === "ArrowDown" || e.key === (rtl ? "ArrowLeft" : "ArrowRight");
  const i = options.findIndex((o) => o.value === model.value);
  const next = options[(i + (forward ? 1 : -1) + options.length) % options.length]!;
  model.value = next.value;
  const group = e.currentTarget as HTMLElement;
  requestAnimationFrame(() => group.querySelector<HTMLElement>('[aria-checked="true"]')?.focus());
}
</script>

<template>
  <div class="seg" :class="[size === 'sm' && 'sm', block && 'block']" role="radiogroup" :aria-label="label" @keydown="onKey($event, options)">
    <button
      v-for="o in options"
      :key="String(o.value)"
      type="button"
      role="radio"
      :aria-checked="model === o.value"
      :tabindex="model === o.value ? 0 : -1"
      :title="o.title"
      @click="model = o.value"
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
  border-radius: var(--r-sm);
  background: var(--surface-2);
  border: 1px solid var(--line);
}
.seg.block {
  display: flex;
}
.seg.block button {
  flex: 1;
}
button {
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-2);
  font-size: var(--fs-xs);
  font-weight: 500;
  white-space: nowrap;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease);
}
.sm button {
  min-height: 28px;
  padding: 0 10px;
}
button:hover {
  color: var(--text);
}
button[aria-checked="true"] {
  background: var(--surface-1);
  color: var(--text);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18), inset 0 0 0 1px var(--line-2);
}
</style>
