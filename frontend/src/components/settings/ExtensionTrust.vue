<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { api } from "@/api/client";

const { t } = useI18n();
const allowed = ref<string[]>([]);
const pending = ref<string[]>([]);
const remote = ref(false);

async function load() {
  try {
    const r = await api.extensions();
    allowed.value = r.allowed;
    pending.value = r.pending;
  } catch {
    remote.value = true; // managed from the computer only
  }
}

async function set(id: string, allow: boolean) {
  const r = await api.setExtension(id, allow);
  allowed.value = r.allowed;
  pending.value = r.pending;
}

onMounted(load);
</script>

<template>
  <div>
    <p class="panel__lead">{{ t("extensions.lead") }}</p>
    <p v-if="remote" class="muted">{{ t("phone.remote") }}</p>
    <template v-else>
      <p v-if="!allowed.length && !pending.length" class="muted">{{ t("extensions.none") }}</p>
      <ul class="list">
        <li v-for="id in pending" :key="'p' + id" class="row row--pending">
          <code dir="ltr" class="mono">{{ id }}</code>
          <span class="tag">{{ t("extensions.waiting") }}</span>
          <button type="button" class="btn btn--primary btn--sm" @click="set(id, true)">{{ t("extensions.allow") }}</button>
          <button type="button" class="btn btn--quiet btn--sm" @click="set(id, false)">{{ t("extensions.dismiss") }}</button>
        </li>
        <li v-for="id in allowed" :key="'a' + id" class="row">
          <code dir="ltr" class="mono">{{ id }}</code>
          <span class="tag tag--ok">{{ t("extensions.allowed") }}</span>
          <button type="button" class="btn btn--quiet btn--sm" @click="set(id, false)">{{ t("extensions.remove") }}</button>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.list {
  list-style: none;
  margin: var(--s-3) 0 0;
  padding: 0;
  display: grid;
  gap: var(--s-2);
}
.row {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  flex-wrap: wrap;
}
.row code {
  font-size: var(--fs-sm);
  word-break: break-all;
}
.tag {
  font-size: var(--fs-xs, 0.8rem);
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(240, 146, 43, 0.16);
}
.tag--ok {
  background: rgba(46, 160, 110, 0.16);
}
</style>
