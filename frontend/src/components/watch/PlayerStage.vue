<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { PhMicrophoneStage, PhWarningCircle, PhWaveform } from "@phosphor-icons/vue";
import SubtitleOverlay from "@/components/SubtitleOverlay.vue";
import AudioStage from "./AudioStage.vue";
import WaveformBar from "./WaveformBar.vue";
import type { AsrState, MediaItem } from "@/api/types";
import ProgressMeter from "@/components/ui/ProgressMeter.vue";
import { api } from "@/api/client";
import { errText } from "@/i18n";
import { liveDub, prewarmDub, startLiveDub, stopLiveDub } from "@/composables/liveDub";
import { openLookup } from "@/composables/lookup";
import { usePrefs } from "@/composables/prefs";
import { attachPlayer, cues, detachPlayer, loadVideo, session, startWhisper, tr } from "@/composables/session";
import { useHealth } from "@/composables/health";
import { isMediaId } from "@/lib/links";
import { html5Player } from "@/player/html5";
import type { Player } from "@/player/types";
import { createYouTubePlayer, suppressNativeCaptions } from "@/player/youtube";
import CopyCommand from "@/components/CopyCommand.vue";

const { t } = useI18n();
const prefs = usePrefs();
const { health } = useHealth();

const frame = ref<HTMLElement | null>(null);
const ytHost = ref<HTMLElement | null>(null);
const video = ref<HTMLVideoElement | null>(null);
const scale = ref(1);
const ytFailed = ref(false);

let player: Player | null = null;
let ytPlayer: (Player & { loadVideoById?(id: string): void }) | null = null;
let stopCC: (() => void) | null = null;
let ro: ResizeObserver | null = null;

const isMedia = computed(() => isMediaId(session.videoId));
const mediaSrc = computed(() => (isMedia.value ? api.mediaFileUrl(session.videoId.slice(6)) : ""));

/* ---------- files from this device: audio or video, its waveform, how Whisper will run ---------- */

const audioStage = ref<InstanceType<typeof AudioStage> | null>(null);
const info = ref<MediaItem | null>(null);
const peaks = ref<number[]>([]);
const asr = ref<AsrState | null>(null);
const mediaId = computed(() => (isMediaId(session.link) ? session.link.slice(6) : ""));
const isAudio = computed(() => !!mediaId.value && info.value?.id === mediaId.value && info.value.kind === "audio");
let infoFor = "";
let infoLoad: Promise<void> | null = null;

function loadInfo(force = false): Promise<void> {
  const id = mediaId.value;
  if (!id) return Promise.resolve();
  if (infoFor === id && infoLoad && !force) return infoLoad;
  if (infoFor !== id) peaks.value = [];
  infoFor = id;
  infoLoad = (async () => {
    try {
      const m = await api.mediaInfo(id);
      if (infoFor !== id) return;
      info.value = m;
      session.audioOnly = m.kind === "audio";
      if (m.kind === "audio" && (!peaks.value.length || !force)) {
        const p = await api.mediaPeaks(id);
        if (infoFor === id) peaks.value = p.peaks;
      }
    } catch {
      /* shown as a video without extras */
    }
  })();
  return infoLoad;
}

watch(
  mediaId,
  (id) => {
    if (!id) session.audioOnly = false;
    else void loadInfo();
  },
  { immediate: true },
);
// After Whisper the file knows its transcript, model and exact length.
watch(
  () => session.whisper && session.phase === "ready",
  (fresh, was) => fresh && was === false && void loadInfo(true),
);

// While Whisper is offered or working: which model it will use, how long it should take, and the
// model download when it is the first time.
let asrTimer: number | undefined;
async function refreshAsr() {
  try {
    asr.value = await api.asr(info.value?.duration || undefined);
  } catch {
    /* the screen works without it */
  }
}
watch(
  () => session.phase === "whisper",
  (on) => {
    clearInterval(asrTimer);
    if (!on) return;
    void refreshAsr();
    asrTimer = window.setInterval(() => session.whisperJob && void refreshAsr(), 2000);
  },
  { immediate: true },
);

const mediaLength = computed(() => info.value?.duration || 0);
watch(mediaLength, () => session.phase === "whisper" && void refreshAsr());
function humanTime(sec: number): string {
  if (sec < 60) return t("watch.whisper.secs", { n: Math.max(5, Math.round(sec / 5) * 5) });
  return t("watch.whisper.mins", { n: Math.round(sec / 60) });
}
const plan = computed(() => {
  const e = asr.value?.effective;
  if (!e) return "";
  const device = t(e.device === "cuda" ? "watch.whisper.gpu" : "watch.whisper.cpu");
  if (mediaLength.value > 0) return t("watch.whisper.planFor", { model: e.model, device, time: humanTime((mediaLength.value / 60) * e.secondsPerMinute) });
  return t("watch.whisper.plan", { model: e.model, device, sec: e.secondsPerMinute });
});
const downloading = computed(() => {
  const l = asr.value?.status.loading;
  if (!l || !session.whisperJob) return "";
  return l.progress != null ? t("watch.whisper.downloading", { model: l.model, pct: l.progress }) : t("watch.whisper.preparing", { model: l.model });
});
/** Whisper's share of the job (30-80%) as the part of the waveform already heard. */
const heard = computed(() => {
  const p = session.whisperJob?.progress ?? 0;
  return Math.max(0, Math.min(1, (p - 30) / 50));
});

const cur = computed(() => (session.curIdx >= 0 ? cues.value[session.curIdx] : undefined));
const curText = computed(() => (session.curIdx >= 0 ? tr.value[session.curIdx] || "" : ""));

/* ---------- creating the player ---------- */

async function mount() {
  if (session.phase !== "ready" || !session.videoId) return;
  stopLiveDub(false);
  detachPlayer();
  prewarmDub();
  await nextTick();
  if (isMedia.value) {
    ytPlayer?.pauseVideo();
    await loadInfo();
    await nextTick();
    const v = isAudio.value ? audioStage.value?.media : video.value;
    if (!v) return;
    if (v.readyState < 1) await new Promise((r) => v.addEventListener("loadedmetadata", r, { once: true }));
    player = html5Player(v);
    attachPlayer(player, afterReady);
    return;
  }
  ytFailed.value = false;
  session.playerError = null;
  try {
    if (ytPlayer && ytHost.value?.querySelector("iframe")) {
      ytPlayer.loadVideoById?.(session.videoId);
      player = ytPlayer;
    } else {
      const h = await createYouTubePlayer(ytHost.value!, session.videoId, {
        hl: prefs.uiLang,
        onError: (code) => (session.playerError = code),
        // Captions come back when playback (re)starts.
        onStateChange: (st) => st === 1 && ytPlayer?.unloadModule?.("captions"),
      });
      ytPlayer = h.player;
      player = h.player;
    }
    stopCC?.();
    stopCC = suppressNativeCaptions(player);
    attachPlayer(player, afterReady);
  } catch {
    ytFailed.value = true;
  }
}

/** Last time the dub was on, it comes back on. */
function afterReady() {
  if (prefs.liveDub) startLiveDub();
}

watch(
  () => [session.phase, session.videoId] as const,
  ([phase], old) => {
    if (phase === "ready" && (old?.[0] !== "ready" || old?.[1] !== session.videoId)) void mount();
  },
);

onMounted(() => {
  ro = new ResizeObserver(([e]) => {
    if (e) scale.value = Math.max(0.55, Math.min(1.8, e.contentRect.width / 900));
  });
  if (frame.value) ro.observe(frame.value);
  if (session.phase === "ready") void mount();
});

onBeforeUnmount(() => {
  clearInterval(asrTimer);
  ro?.disconnect();
  stopCC?.();
  stopLiveDub(false);
  detachPlayer();
  try {
    ytPlayer?.destroy();
  } catch {
    /* already gone */
  }
  ytPlayer = null;
});

/* ---------- fullscreen ---------- */

function toggleFullscreen() {
  if (!document.fullscreenElement) frame.value?.requestFullscreen?.().catch(() => {});
  else void document.exitFullscreen?.();
}
defineExpose({ toggleFullscreen });

function onDbl(e: MouseEvent) {
  if (session.phase === "ready" && !(e.target as Element).closest(".subs .w, button, [role=slider]")) toggleFullscreen();
}

function onWord(word: string, el: Element) {
  if (session.curIdx >= 0) void openLookup(word, session.curIdx, el);
}

const dubLabel = computed(() => {
  const s = liveDub.state;
  return t("dub.state." + (["speaking", "catching-up", "waiting", "buffering", "error"].includes(s) ? s : "ready"));
});

const uiDir = computed(() => (prefs.uiLang === "ar" ? "rtl" : "ltr"));
const whisperMissing = computed(() => health.value && !health.value.whisper?.installed);
const retry = () => loadVideo(session.link);
</script>

<template>
  <section ref="frame" class="stage" :class="{ live: session.phase === 'ready' }" :aria-label="$t('watch.player')" @dblclick="onDbl">
    <!-- YouTube player host (kept mounted so the iframe can be reused between videos) -->
    <div v-show="session.phase === 'ready' && !isMedia" ref="ytHost" class="yt"></div>
    <video v-if="session.phase === 'ready' && isMedia && !isAudio" ref="video" class="media" :src="mediaSrc" controls playsinline preload="auto"></video>
    <AudioStage
      v-if="session.phase === 'ready' && isAudio"
      ref="audioStage"
      :src="mediaSrc"
      :title="session.title || info?.title || ''"
      :peaks="peaks"
      :duration="info?.duration || 0"
      :model="info?.asr || ''"
    >
      <SubtitleOverlay
        :src="cur?.src || ''"
        :text="curText"
        :pending="!!cur && !curText"
        :bilingual="prefs.bilingual && !session.sameLang"
        position="bottom"
        :size="Math.round(prefs.size * 1.25)"
        :font="prefs.font"
        :bgo="0"
        :quiz="prefs.quiz"
        :hidden="!prefs.show"
        :rtl="session.tl === 'ar'"
        :scale="scale"
        inline
        @word="onWord"
      />
    </AudioStage>

    <template v-if="session.phase === 'ready'">
      <SubtitleOverlay
        v-if="!isAudio"
        :src="cur?.src || ''"
        :text="curText"
        :pending="!!cur && !curText"
        :bilingual="prefs.bilingual && !session.sameLang"
        :position="prefs.position"
        :size="prefs.size"
        :font="prefs.font"
        :bgo="prefs.bgo"
        :quiz="prefs.quiz"
        :hidden="!prefs.show"
        :rtl="session.tl === 'ar'"
        :scale="scale"
        @word="onWord"
      />
      <div v-if="liveDub.on" class="dub-badge" :class="liveDub.state" :dir="uiDir" role="status">
        <i aria-hidden="true"></i>
        <span>{{ dubLabel }}</span>
      </div>
      <div v-if="ytFailed" class="over" :dir="uiDir">
        <PhWarningCircle :size="32" />
        <h2>{{ $t("watch.ytFailed.title") }}</h2>
        <p>{{ $t("watch.ytFailed.body") }}</p>
        <button class="btn btn--primary" type="button" @click="mount">{{ $t("common.retry") }}</button>
      </div>
      <div v-else-if="session.playerError" class="over soft" :dir="uiDir">
        <PhWarningCircle :size="28" />
        <p>{{ session.playerError === 101 || session.playerError === 150 ? $t("watch.embedBlocked") : $t("watch.playerError", { code: session.playerError }) }}</p>
      </div>
    </template>

    <!-- loading -->
    <div v-else-if="session.phase === 'loading' || session.phase === 'idle'" class="over" :dir="uiDir">
      <div class="spinner" aria-hidden="true"></div>
      <p>{{ $t("watch.loading") }}</p>
    </div>

    <!-- no captions: offer Whisper -->
    <div v-else-if="session.phase === 'whisper'" class="over" :class="{ 'over--audio': isAudio }" :dir="uiDir">
      <div v-if="isAudio" class="pre-wave" dir="ltr">
        <WaveformBar :peaks="peaks" :progress="heard" :duration="mediaLength" :scanning="!!session.whisperJob" :label="$t('watch.audio.badge')" />
      </div>
      <PhWaveform v-else :size="36" class="accent" />
      <h2>{{ isAudio ? $t("watch.whisper.titleAudio") : isMediaId(session.link) ? $t("watch.whisper.titleLocal") : $t("watch.whisper.title") }}</h2>
      <p>{{ isAudio ? $t("watch.whisper.bodyAudio") : isMediaId(session.link) ? $t("watch.whisper.bodyLocal") : $t("watch.whisper.body") }}</p>
      <template v-if="whisperMissing">
        <p class="small">{{ $t("watch.whisper.missing") }}</p>
        <CopyCommand cmd="python -m tarjuman setup" />
      </template>
      <div v-else-if="session.whisperJob" class="meter-wrap">
        <ProgressMeter :value="session.whisperJob.progress" :label="(session.whisperJob.phase || $t('watch.whisper.working')) + ' · ' + Math.round(session.whisperJob.progress) + '%'" />
      </div>
      <button v-else class="btn btn--primary btn--lg" type="button" @click="startWhisper">
        <PhMicrophoneStage :size="18" />
        {{ session.error.code ? $t("common.retry") : isAudio ? $t("watch.whisper.startAudio") : $t("watch.whisper.start") }}
      </button>
      <p v-if="downloading" class="small" role="status">{{ downloading }}</p>
      <p v-if="session.error.code" class="err" role="alert">{{ errText(session.error.code, session.error.message, true) }}</p>
      <p v-if="!whisperMissing" class="small">
        {{ plan || $t("watch.whisper.note") }}
        <RouterLink class="link" :to="{ name: 'settings', hash: '#transcription' }">{{ $t("watch.whisper.tune") }}</RouterLink>
      </p>
    </div>

    <!-- error -->
    <div v-else-if="session.phase === 'error'" class="over" :dir="uiDir">
      <PhWarningCircle :size="32" class="danger" />
      <h2>{{ $t("watch.error.title") }}</h2>
      <p>{{ errText(session.error.code, session.error.message) }}</p>
      <CopyCommand v-if="session.error.code === 'NO_SERVER'" cmd="python -m tarjuman" />
      <div class="row">
        <button class="btn btn--primary" type="button" @click="retry">{{ $t("common.retry") }}</button>
        <RouterLink class="btn btn--outline" to="/">{{ $t("watch.error.other") }}</RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stage {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  max-height: calc(100dvh - var(--header-h) - 120px);
  border-radius: var(--r-lg);
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(90% 70% at 80% 0%, rgba(255, 210, 122, 0.08), transparent 60%),
    linear-gradient(165deg, var(--lapis-700), var(--lapis-900) 70%);
  color: #eef0fb;
  box-shadow: var(--shadow-2), 0 0 0 1px var(--line);
  direction: ltr;
}
.stage.live {
  background: var(--player-ground);
}
.stage:fullscreen {
  border-radius: 0;
  max-height: none;
}
.yt,
.yt :deep(iframe),
.media {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}
.media {
  background: var(--player-ground);
  z-index: 1;
}
.over {
  position: absolute;
  inset: 0;
  z-index: 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--s-3);
  padding: 6%;
  text-align: center;
}
.over.soft {
  inset: auto 0 0 0;
  padding: var(--s-3) var(--s-5);
  flex-direction: row;
  background: rgba(5, 7, 26, 0.85);
  font-size: var(--fs-sm);
}
.over h2 {
  font-family: var(--font-display);
  font-size: clamp(20px, 2.6vw, 30px);
  color: #fff;
}
.over p {
  max-width: 56ch;
  color: #c3c8e6;
  font-size: var(--fs-sm);
}
.over .small {
  font-size: var(--fs-xs);
  color: #9aa2cf;
}
.over--audio {
  gap: var(--s-2);
}
.pre-wave {
  width: min(560px, 92%);
  height: clamp(56px, 14vh, 96px);
  margin-bottom: var(--s-2);
}
.over .link {
  color: var(--saffron-300);
  text-decoration: underline;
  text-underline-offset: 3px;
  margin-inline-start: 6px;
}
.over .err {
  color: #ffb4b4;
}
.over .accent {
  color: var(--saffron-300);
}
.over .danger {
  color: #ffb4b4;
}
.over .row {
  display: flex;
  gap: var(--s-2);
  flex-wrap: wrap;
  justify-content: center;
}
.over :deep(.cmd) {
  background: rgba(0, 0, 0, 0.35);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.15);
}
.over .btn--outline {
  --btn-fg: #fff;
  --btn-line: rgba(255, 255, 255, 0.3);
}
.over .btn--outline:hover {
  --btn-bg: rgba(255, 255, 255, 0.08);
}
.meter-wrap {
  width: min(440px, 100%);
}
.meter-wrap :deep(.lbl) {
  color: #c3c8e6;
}
.meter-wrap :deep(.track) {
  background: rgba(255, 255, 255, 0.12);
}
.spinner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.15);
  border-top-color: var(--saffron-300);
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.dub-badge {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: var(--r-pill);
  background: rgba(5, 7, 26, 0.82);
  border: 1px solid rgba(255, 210, 122, 0.35);
  font-size: 13px;
  font-weight: 500;
  pointer-events: none;
}
.dub-badge i {
  width: 8px;
  height: 8px;
  border-radius: 1px;
  transform: rotate(45deg);
  background: var(--saffron-300);
}
.dub-badge.speaking i,
.dub-badge.catching-up i {
  animation: pulse 1s ease-in-out infinite;
}
.dub-badge.waiting,
.dub-badge.buffering {
  border-color: rgba(127, 220, 176, 0.5);
}
.dub-badge.waiting i,
.dub-badge.buffering i {
  background: #7fdcb0;
}
.dub-badge.error {
  border-color: rgba(255, 154, 154, 0.5);
}
@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}
@media (max-width: 759px) {
  .stage {
    border-radius: 0;
    max-height: none;
  }
  .over {
    padding: var(--s-4);
    gap: var(--s-2);
  }
  .over p {
    font-size: var(--fs-xs);
  }
}
</style>
