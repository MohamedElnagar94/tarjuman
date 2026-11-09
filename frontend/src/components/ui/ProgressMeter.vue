<script setup lang="ts">
defineProps<{ value: number; label?: string; tone?: "accent" | "ok" | "danger" }>();
</script>

<template>
  <div class="meter" :class="tone">
    <div class="track" role="progressbar" :aria-valuenow="Math.round(value)" aria-valuemin="0" aria-valuemax="100" :aria-label="label">
      <i :style="{ transform: `scaleX(${Math.max(0, Math.min(100, value)) / 100})` }"></i>
    </div>
    <span v-if="label" class="lbl">{{ label }}</span>
  </div>
</template>

<style scoped>
.meter {
  display: grid;
  gap: 6px;
  width: 100%;
}
.track {
  height: 6px;
  border-radius: var(--r-pill);
  background: var(--surface-3);
  overflow: hidden;
}
i {
  display: block;
  height: 100%;
  background: var(--accent-strong);
  border-radius: inherit;
  transform-origin: var(--start);
  transition: transform 400ms var(--ease);
}
.ok i {
  background: var(--ok);
}
.danger i {
  background: var(--danger);
}
.lbl {
  font-size: var(--fs-xs);
  color: var(--text-2);
}
</style>
