<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import { PhX } from "@phosphor-icons/vue";

/* Native <dialog>: focus trapping, Esc and the top layer come for free. */
const props = defineProps<{ title: string; wide?: boolean }>();
const open = defineModel<boolean>({ required: true });
const el = ref<HTMLDialogElement | null>(null);

watch(
  open,
  async (v) => {
    await nextTick();
    const d = el.value;
    if (!d) return;
    if (v && !d.open) d.showModal();
    else if (!v && d.open) d.close();
  },
  { immediate: true },
);

function onBackdrop(e: MouseEvent) {
  if (e.target === el.value) open.value = false;
}
</script>

<template>
  <dialog ref="el" class="dlg" :class="{ wide: props.wide }" :aria-label="props.title" @close="open = false" @click="onBackdrop">
    <div class="dlg__in">
      <header class="dlg__head">
        <h2 class="dlg__title">{{ props.title }}</h2>
        <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="$t('common.close')" @click="open = false"><PhX :size="18" /></button>
      </header>
      <slot />
    </div>
  </dialog>
</template>

<style scoped>
.dlg {
  width: min(520px, calc(100vw - 32px));
  max-height: min(80dvh, 720px);
  padding: 0;
  border: 1px solid var(--line-2);
  border-radius: var(--r-lg);
  background: var(--surface-1);
  color: var(--text);
  box-shadow: var(--shadow-2);
}
.dlg.wide {
  width: min(720px, calc(100vw - 32px));
}
.dlg::backdrop {
  background: var(--scrim);
  backdrop-filter: blur(2px);
}
.dlg[open] {
  animation: rise 180ms var(--ease);
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
}
.dlg__in {
  padding: var(--s-5);
}
.dlg__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  margin-bottom: var(--s-4);
}
.dlg__title {
  font-family: var(--font-display);
  font-size: var(--fs-xl);
}
</style>
