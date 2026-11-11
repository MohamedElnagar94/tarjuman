<script setup lang="ts">
import { useI18n } from "vue-i18n";

const { t } = useI18n();

// One row per feature that talks to the network, then the ones that never do.
// "where" is who receives it; "local" is how to do the same without sending anything.
const ROWS = [
  { id: "captions", online: true },
  { id: "translate", online: true },
  { id: "voice", online: true },
  { id: "fetch", online: true },
  { id: "ai", online: true },
  { id: "models", online: true },
  { id: "whisper", online: false },
  { id: "separate", online: false },
  { id: "files", online: false },
] as const;
</script>

<template>
  <div>
    <p class="panel__lead">{{ t("privacy.lead") }}</p>
    <ul class="flow">
      <li v-for="r in ROWS" :key="r.id" class="row">
        <div class="row__head">
          <strong>{{ t(`privacy.${r.id}.name`) }}</strong>
          <span class="tag" :class="r.online ? 'tag--out' : 'tag--in'">{{ t(r.online ? "privacy.online" : "privacy.offline") }}</span>
        </div>
        <p class="row__what">{{ t(`privacy.${r.id}.what`) }}</p>
        <p v-if="r.online" class="row__local muted">{{ t(`privacy.${r.id}.local`) }}</p>
      </li>
    </ul>
    <p class="muted small">{{ t("privacy.never") }}</p>
  </div>
</template>

<style scoped>
.flow {
  list-style: none;
  margin: var(--s-3) 0;
  padding: 0;
  display: grid;
  gap: var(--s-2);
}
.row {
  padding: var(--s-3) var(--s-4);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--surface-2);
}
.row__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  flex-wrap: wrap;
}
.row__what {
  margin: var(--s-2) 0 0;
  line-height: 1.8;
}
.row__local {
  margin: var(--s-1) 0 0;
  font-size: var(--fs-sm);
  line-height: 1.8;
}
.tag {
  padding: 2px 10px;
  border-radius: var(--r-pill);
  font-size: var(--fs-xs);
  white-space: nowrap;
}
.tag--out {
  background: var(--accent-soft);
  border: 1px solid var(--accent-line);
  color: var(--text);
}
.tag--in {
  background: var(--ok-soft);
  color: var(--ok);
}
.small {
  font-size: var(--fs-sm);
}
</style>
