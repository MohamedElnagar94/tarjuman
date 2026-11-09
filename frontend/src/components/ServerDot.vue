<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { useHealth } from "@/composables/health";

const { t } = useI18n();
const { status, health } = useHealth();

const tone = computed(() => {
  if (status.value === "down") return "down";
  if (status.value === "unknown" || !health.value) return "unknown";
  const h = health.value;
  return h.whisper.installed && h.tts.installed ? "up" : "partial";
});
const label = computed(() => t("status.dot." + tone.value));
</script>

<template>
  <RouterLink to="/#status" class="dot" :class="tone" :title="label" :aria-label="label">
    <i aria-hidden="true"></i>
    <span class="txt">{{ label }}</span>
  </RouterLink>
</template>

<style scoped>
.dot {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 10px;
  border-radius: var(--r-pill);
  color: var(--text-2);
  text-decoration: none;
  font-size: var(--fs-xs);
}
.dot:hover {
  background: var(--surface-1);
  color: var(--text);
}
.dot i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-3);
}
.up i {
  background: var(--ok);
}
.partial i {
  background: var(--accent-strong);
}
.down i {
  background: var(--danger);
}
.down {
  color: var(--danger);
}
@media (max-width: 1240px) {
  .txt {
    display: none;
  }
}
</style>
