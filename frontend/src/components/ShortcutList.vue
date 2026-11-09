<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { SHORTCUTS } from "@/composables/shortcuts";

const { t } = useI18n();
</script>

<template>
  <dl class="keys">
    <template v-for="s in SHORTCUTS" :key="s.id">
      <dt>
        <kbd v-for="k in s.keys" :key="k">{{ k }}</kbd>
      </dt>
      <dd>{{ t("shortcuts." + s.id) }}</dd>
    </template>
  </dl>
</template>

<style scoped>
.keys {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px 18px;
  margin: 0;
  align-items: center;
  font-size: var(--fs-sm);
}
dt {
  display: flex;
  gap: 4px;
}
dd {
  margin: 0;
  color: var(--text-2);
}
</style>
