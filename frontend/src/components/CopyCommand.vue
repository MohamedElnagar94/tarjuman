<script setup lang="ts">
import { ref } from "vue";
import { PhCheck, PhCopy } from "@phosphor-icons/vue";

const props = defineProps<{ cmd: string }>();
const copied = ref(false);

async function copy() {
  try {
    await navigator.clipboard.writeText(props.cmd);
    copied.value = true;
    setTimeout(() => (copied.value = false), 1800);
  } catch {
    /* clipboard needs a secure context; the text is still selectable */
  }
}
</script>

<template>
  <span class="cc">
    <code class="cmd">{{ cmd }}</code>
    <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="copied ? $t('common.copied') : $t('common.copyCommand')" @click="copy">
      <PhCheck v-if="copied" :size="15" />
      <PhCopy v-else :size="15" />
    </button>
  </span>
</template>

<style scoped>
.cc {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  max-width: 100%;
}
</style>
