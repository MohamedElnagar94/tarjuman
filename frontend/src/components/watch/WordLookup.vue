<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { PhBookmarkSimple, PhCheck, PhSpeakerHigh, PhX } from "@phosphor-icons/vue";
import { closeLookup, lookup, saveLookup, srcLangCode } from "@/composables/lookup";
import { toast } from "@/composables/toast";
import { playTts } from "@/composables/voices";

const { t } = useI18n();
const el = ref<HTMLElement | null>(null);
const pos = ref({ top: 0, left: 0 });

async function place() {
  await nextTick();
  const box = el.value;
  if (!box) return;
  const r = lookup.rect;
  const h = box.offsetHeight;
  const w = box.offsetWidth;
  const below = r.bottom + 8 + h <= innerHeight;
  pos.value = {
    top: Math.max(8, below ? r.bottom + 8 : r.top - h - 8),
    left: Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)),
  };
  box.querySelector<HTMLElement>(".primary")?.focus({ preventScroll: true });
}
watch(() => [lookup.open, lookup.word], () => lookup.open && place());
watch(() => lookup.status, () => lookup.open && place());

function onDown(e: MouseEvent) {
  if (!lookup.open) return;
  const target = e.target as Element;
  if (el.value?.contains(target) || target.closest(".w")) return;
  closeLookup();
}
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape" && lookup.open) closeLookup();
}
onMounted(() => {
  document.addEventListener("mousedown", onDown);
  document.addEventListener("keydown", onKey);
  window.addEventListener("resize", closeLookup);
});
onBeforeUnmount(() => {
  document.removeEventListener("mousedown", onDown);
  document.removeEventListener("keydown", onKey);
  window.removeEventListener("resize", closeLookup);
  closeLookup();
});

async function listen() {
  try {
    await playTts(lookup.word, srcLangCode());
  } catch {
    toast(t("lookup.noAudio"), { tone: "danger" });
  }
}

const saveLabel = () =>
  ({ idle: t("lookup.save"), saving: t("lookup.saving"), saved: t("lookup.saved"), duplicate: t("lookup.duplicate"), error: t("lookup.saveFailed") })[lookup.save];
</script>

<template>
  <Teleport to="body">
    <div v-if="lookup.open" ref="el" class="lk" role="dialog" :aria-label="t('lookup.title', { word: lookup.word })" :style="{ top: pos.top + 'px', left: pos.left + 'px' }">
      <div class="lk__head">
        <span class="lk__word ltr" lang="en">{{ lookup.word }}</span>
        <button type="button" class="btn btn--quiet btn--icon btn--sm" :aria-label="t('common.close')" @click="closeLookup"><PhX :size="16" /></button>
      </div>
      <p class="lk__tr" aria-live="polite">
        <span v-if="lookup.status === 'loading'" class="skeleton line"></span>
        <template v-else-if="lookup.status === 'ok'">{{ lookup.meaning }}</template>
        <span v-else class="muted">{{ lookup.status === "none" ? t("lookup.none") : t("lookup.failed") }}</span>
      </p>
      <p v-if="lookup.sentence" class="lk__ctx ltr" lang="en">{{ lookup.sentence }}</p>
      <div class="lk__actions">
        <button type="button" class="btn btn--primary btn--sm primary" :disabled="lookup.save !== 'idle' && lookup.save !== 'error'" @click="saveLookup">
          <PhCheck v-if="lookup.save === 'saved' || lookup.save === 'duplicate'" :size="16" />
          <PhBookmarkSimple v-else :size="16" />
          {{ saveLabel() }}
        </button>
        <button type="button" class="btn btn--outline btn--sm" @click="listen"><PhSpeakerHigh :size="16" />{{ t("lookup.listen") }}</button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.lk {
  position: fixed;
  z-index: var(--z-popover);
  width: min(320px, calc(100vw - 16px));
  padding: var(--s-4);
  border-radius: var(--r-md);
  background: var(--surface-1);
  border: 1px solid var(--line-2);
  box-shadow: var(--shadow-2);
  animation: pop 140ms var(--ease);
}
@keyframes pop {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}
.lk__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-2);
}
.lk__word {
  font-size: var(--fs-xl);
  font-weight: 600;
}
.lk__tr {
  font-size: var(--fs-lg);
  margin: 4px 0 var(--s-2);
  min-height: 1.7em;
}
.line {
  display: block;
  width: 60%;
  height: 16px;
  margin-top: 6px;
}
.lk__ctx {
  font-size: var(--fs-xs);
  color: var(--text-2);
  margin-bottom: var(--s-3);
  text-align: left;
}
.lk__actions {
  display: flex;
  gap: var(--s-2);
  flex-wrap: wrap;
}
</style>
