<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";
import { PhTrash } from "@phosphor-icons/vue";

/* Deleting takes two taps: the first arms the button for a few seconds. No modal needed. */
const props = defineProps<{ label: string; confirmLabel: string; icon?: boolean }>();
const emit = defineEmits<{ confirm: [] }>();
const armed = ref(false);
let timer: number | undefined;

function click() {
  if (armed.value) {
    armed.value = false;
    window.clearTimeout(timer);
    emit("confirm");
    return;
  }
  armed.value = true;
  timer = window.setTimeout(() => (armed.value = false), 4000);
}
onBeforeUnmount(() => window.clearTimeout(timer));
</script>

<template>
  <button
    type="button"
    class="btn btn--sm"
    :class="armed ? 'btn--danger armed' : 'btn--quiet'"
    :aria-label="props.icon && !armed ? props.label : undefined"
    @click="click"
  >
    <PhTrash v-if="props.icon || armed" :size="16" />
    <span v-if="!props.icon || armed">{{ armed ? props.confirmLabel : props.label }}</span>
  </button>
</template>

<style scoped>
.armed {
  border-color: var(--danger-line);
}
</style>
