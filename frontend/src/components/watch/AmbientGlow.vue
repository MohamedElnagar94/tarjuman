<script setup lang="ts">
/* A soft light behind the player in the video's own colours, like a TV that lights the wall. For a
   video from this computer the light follows the picture (a tiny copy of the frame, twice a second);
   for YouTube, whose frames can't be read, it is the video's thumbnail. It breathes a little while the
   video plays and dims when it pauses. */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { session } from "@/composables/session";
import { isMediaId } from "@/lib/links";

const canvas = ref<HTMLCanvasElement | null>(null);
let timer: number | undefined;

const media = computed(() => isMediaId(session.videoId));
const thumb = computed(() =>
  !media.value && /^[\w-]{11}$/.test(session.videoId) ? `url("https://i.ytimg.com/vi/${session.videoId}/hqdefault.jpg")` : "",
);

function sample() {
  const c = canvas.value;
  const v = document.querySelector<HTMLVideoElement>(".stage video.media");
  if (!c || !v || v.readyState < 2) return;
  const g = c.getContext("2d", { willReadFrequently: false });
  try {
    g?.drawImage(v, 0, 0, c.width, c.height);
  } catch {
    /* not ready */
  }
}
function start() {
  stop();
  if (!media.value) return;
  sample();
  timer = window.setInterval(() => session.playing && sample(), 500);
}
function stop() {
  window.clearInterval(timer);
}
watch(media, start);
watch(() => session.videoId, start);
onMounted(start);
onBeforeUnmount(stop);
</script>

<template>
  <div class="glow" :class="{ playing: session.playing, media }" aria-hidden="true">
    <canvas v-if="media" ref="canvas" width="32" height="18"></canvas>
    <div v-else-if="thumb" class="img" :style="{ backgroundImage: thumb }"></div>
  </div>
</template>

<style scoped>
.glow {
  position: absolute;
  inset: -3% -2% -6%;
  z-index: 0;
  pointer-events: none;
  opacity: 0.32;
  filter: blur(60px) saturate(1.5);
  transition: opacity 900ms var(--ease);
}
.glow.playing {
  opacity: 0.6;
}
.glow canvas,
.glow .img {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  border-radius: 40px;
}
.glow.playing .img,
.glow.playing canvas {
  animation: breathe 9s ease-in-out infinite;
}
@keyframes breathe {
  50% {
    transform: scale(1.05);
  }
}
:root[data-theme="light"] .glow,
.light .glow {
  opacity: 0.22;
}
/* On a phone the player fills the width: there is no wall to light. */
@media (max-width: 759px) {
  .glow {
    display: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .glow.playing .img,
  .glow.playing canvas {
    animation: none;
  }
}
</style>
