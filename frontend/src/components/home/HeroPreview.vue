<script setup lang="ts">
import { useI18n } from "vue-i18n";
import SubtitleOverlay from "@/components/SubtitleOverlay.vue";

/* A live preview of the real subtitle component on a lapis "illuminated" panel: it shows
   what the product does before anything is loaded. */
const { t } = useI18n();
</script>

<template>
  <figure class="preview" aria-hidden="true">
    <div class="frame">
      <div class="pattern"></div>
      <div class="badge"><i></i>{{ t("home.preview.badge") }}</div>
      <SubtitleOverlay
        class="sample"
        src="The interpreter turns every sentence into your language, right on time."
        :text="t('home.preview.line')"
        bilingual
        position="bottom"
        :size="22"
        :bgo="0.72"
        rtl
        inline
      />
    </div>
  </figure>
</template>

<style scoped>
.preview {
  margin: 0;
}
.frame {
  position: relative;
  aspect-ratio: 16 / 10;
  border-radius: var(--r-lg);
  overflow: hidden;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 0 6% 8%;
  background:
    radial-gradient(120% 80% at 85% 0%, rgba(255, 210, 122, 0.16), transparent 55%),
    linear-gradient(160deg, var(--lapis-500) 0%, var(--lapis-700) 48%, var(--lapis-900) 100%);
  box-shadow: var(--shadow-2), inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}
/* Manuscript margin: a hairline saffron rule inside the frame. */
.frame::after {
  content: "";
  position: absolute;
  inset: 10px;
  border: 1px solid rgba(255, 210, 122, 0.28);
  border-radius: calc(var(--r-lg) - 8px);
  pointer-events: none;
}
/* Diamond lattice, the same diamonds as the dots of the ت in the mark. */
.pattern {
  position: absolute;
  inset: 0;
  z-index: -1;
  opacity: 0.12;
  background-image:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.9) 0 1px, transparent 1px 28px),
    repeating-linear-gradient(-45deg, rgba(255, 255, 255, 0.9) 0 1px, transparent 1px 28px);
  mask-image: radial-gradient(90% 70% at 70% 30%, #000 0%, transparent 75%);
}
.badge {
  position: absolute;
  top: 26px;
  inset-inline-start: 26px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: var(--r-pill);
  background: rgba(5, 7, 26, 0.62);
  border: 1px solid rgba(255, 210, 122, 0.35);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
}
.badge i {
  width: 8px;
  height: 8px;
  transform: rotate(45deg);
  border-radius: 1px;
  background: var(--saffron-300);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}
.sample :deep(.w:nth-of-type(2)) {
  background: rgba(255, 210, 122, 0.34);
}
</style>
