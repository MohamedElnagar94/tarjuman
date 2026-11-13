<script setup lang="ts">
import { computed } from "vue";
import { langDir, type Settings } from "@/shared/settings";
import { FONT_STACK } from "@/shared/fonts";
import { t } from "@/shared/i18n";

const props = withDefaults(defineProps<{ settings: Settings; active?: boolean; scale?: number; label?: string }>(), { scale: 0.58 });

const SAMPLE: Record<string, string> = {
  ar: "وهكذا بدأت الحكاية كلها.",
  en: "And that's how it all began.",
  fr: "Et c'est ainsi que tout a commencé.",
  es: "Y así es como empezó todo.",
  de: "Und so hat alles angefangen.",
  tr: "Ve her şey böyle başladı.",
};
const SOURCE = "And that's how the whole story began.";

const sample = computed(() => SAMPLE[props.settings.lang] || SAMPLE.ar);
const style = computed(() => ({
  "--fs": Math.round(props.settings.size * props.scale) + "px",
  "--bgo": String(props.settings.bgOpacity),
  fontFamily: FONT_STACK[props.settings.font],
}));
</script>

<template>
  <figure class="screen" :class="{ on: active }" :aria-label="t('previewLabel')">
    <div class="scene" aria-hidden="true">
      <span class="sun"></span>
      <span class="hill a"></span>
      <span class="hill b"></span>
    </div>
    <figcaption v-if="label" class="mode"><span class="live"></span>{{ label }}</figcaption>
    <div class="sample" :class="settings.position" :style="style">
      <div v-if="settings.bilingual" class="src" dir="ltr"><span>{{ SOURCE }}</span></div>
      <div class="tr" :dir="langDir(settings.lang)"><span>{{ sample }}</span></div>
    </div>
    <div class="bar" aria-hidden="true"><i></i></div>
  </figure>
</template>

<style scoped>
.screen {
  position: relative;
  margin: 0;
  aspect-ratio: 16 / 8.4;
  border-radius: 14px;
  overflow: hidden;
  isolation: isolate;
  border: 1px solid var(--line-strong);
  box-shadow: 0 18px 40px -20px rgba(0, 0, 0, 0.8);
}
.scene {
  position: absolute;
  inset: 0;
  z-index: -1;
  background: linear-gradient(180deg, #1B2672 0%, #3A3F9A 42%, #C9774A 78%, #E9A35E 100%);
}
.sun {
  position: absolute;
  width: 38%;
  aspect-ratio: 1;
  left: 54%;
  top: 38%;
  border-radius: 50%;
  background: radial-gradient(circle, #FFE3A8 0%, #FFC46A 45%, rgba(255, 196, 106, 0) 70%);
  opacity: 0.85;
}
.hill {
  position: absolute;
  left: -10%;
  right: -10%;
  border-radius: 50% 50% 0 0;
}
.hill.a {
  bottom: -38%;
  height: 70%;
  background: #121A57;
  left: -30%;
  right: 30%;
}
.hill.b {
  bottom: -46%;
  height: 72%;
  background: #0A0F3A;
  left: 20%;
  right: -40%;
}
.screen::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 80% at 50% 0%, transparent 50%, rgba(0, 0, 0, 0.35));
  pointer-events: none;
}
.mode {
  position: absolute;
  top: 9px;
  inset-inline-start: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  border-radius: 99px;
  background: rgba(10, 15, 58, 0.72);
  border: 1px solid var(--line-strong);
  font-size: 11.5px;
  font-weight: 600;
  color: var(--parchment);
  backdrop-filter: blur(6px);
  z-index: 2;
}
.live {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--muted);
}
.on .live {
  background: var(--saffron-300);
  box-shadow: 0 0 0 3px rgba(255, 210, 122, 0.25);
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}
.sample {
  position: absolute;
  inset-inline: 7%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  z-index: 1;
  transition: top 0.2s var(--ease), bottom 0.2s var(--ease);
}
.sample.bottom {
  bottom: 14%;
}
.sample.top {
  top: 22%;
}
.sample span {
  background: rgba(8, 10, 30, var(--bgo, 0.78));
  color: #fff;
  padding: 0.06em 0.45em 0.1em;
  border-radius: 0.3em;
  line-height: 1.5;
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.9), 0 1px 3px rgba(0, 0, 0, 0.8);
}
.tr {
  font-weight: 700;
  font-size: var(--fs, 15px);
}
.src {
  font-weight: 500;
  font-size: calc(var(--fs, 15px) * 0.62);
  margin-bottom: 0.15em;
}
.src span {
  color: #ECE8DA;
}
.bar {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 7px;
  height: 3px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.25);
}
.bar i {
  display: block;
  width: 38%;
  height: 100%;
  border-radius: 3px;
  background: var(--saffron-300);
}
</style>
