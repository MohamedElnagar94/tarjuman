<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhBookOpenText, PhChatsCircle, PhDownloadSimple, PhMonitorPlay, PhTextAlignRight } from "@phosphor-icons/vue";
import AppDialog from "@/components/ui/AppDialog.vue";
import ShortcutList from "@/components/ShortcutList.vue";
import AskPanel from "@/components/watch/AskPanel.vue";
import ExportPanel from "@/components/watch/ExportPanel.vue";
import LearnPanel from "@/components/watch/LearnPanel.vue";
import PlayerStage from "@/components/watch/PlayerStage.vue";
import PlayerToolbar from "@/components/watch/PlayerToolbar.vue";
import TranscriptPanel from "@/components/watch/TranscriptPanel.vue";
import VideoMeta from "@/components/watch/VideoMeta.vue";
import WatchPanel from "@/components/watch/WatchPanel.vue";
import WordLookup from "@/components/watch/WordLookup.vue";
import { liveDub, toggleLiveDub } from "@/composables/liveDub";
import { closeLookup } from "@/composables/lookup";
import { useMediaQuery } from "@/composables/media";
import { SUB_SIZE, usePrefs } from "@/composables/prefs";
import { armLoop, endSession, loadVideo, session, stepLine, togglePlay } from "@/composables/session";
import { useShortcuts } from "@/composables/shortcuts";
import { toast } from "@/composables/toast";
import { resumeVideoJobs } from "@/composables/videoJobs";
import { parseTime } from "@/lib/time";

type Tab = "transcript" | "watch" | "export" | "ask" | "learn";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const prefs = usePrefs();
const wide = useMediaQuery("(min-width: 1100px)");

const stage = ref<InstanceType<typeof PlayerStage> | null>(null);
const transcript = ref<InstanceType<typeof TranscriptPanel> | null>(null);
const showKeys = ref(false);
const tab = ref<Tab>("watch");

const tabs = computed(() => {
  const all: { id: Tab; icon: unknown }[] = [
    { id: "transcript", icon: PhTextAlignRight },
    { id: "watch", icon: PhMonitorPlay },
    { id: "export", icon: PhDownloadSimple },
    { id: "ask", icon: PhChatsCircle },
    { id: "learn", icon: PhBookOpenText },
  ];
  return wide.value ? all.filter((x) => x.id !== "transcript") : all;
});
watch(
  wide,
  (w) => {
    if (w && tab.value === "transcript") tab.value = "watch";
    if (!w && tab.value === "watch" && session.phase !== "ready") tab.value = "transcript";
  },
  { immediate: true },
);

/* ---------- loading from the URL ---------- */

const urlParam = computed(() => String(route.query.url || ""));
watch(
  urlParam,
  (url) => {
    if (!url) return void router.replace({ name: "home" });
    if (url === session.link && session.phase !== "error" && session.phase !== "idle") return;
    void loadVideo(url, { seek: parseTime(String(route.query.t ?? "")) });
  },
  { immediate: true },
);
watch(
  () => session.phase === "ready" && session.videoId,
  (id) => id && resumeVideoJobs(id),
);
onBeforeUnmount(() => {
  closeLookup();
  endSession();
  document.title = t("app.name");
});

/* ---------- keyboard ---------- */

function selectTab(id: Tab) {
  tab.value = id;
}

function onTabKey(e: KeyboardEvent) {
  const ids = tabs.value.map((x) => x.id);
  const i = ids.indexOf(tab.value);
  const rtl = prefs.uiLang === "ar";
  let n = i;
  if (e.key === (rtl ? "ArrowLeft" : "ArrowRight")) n = (i + 1) % ids.length;
  else if (e.key === (rtl ? "ArrowRight" : "ArrowLeft")) n = (i - 1 + ids.length) % ids.length;
  else if (e.key === "Home") n = 0;
  else if (e.key === "End") n = ids.length - 1;
  else return;
  e.preventDefault();
  e.stopPropagation();
  tab.value = ids[n]!;
  (document.getElementById("tab-" + ids[n]) as HTMLElement | null)?.focus();
}

const ready = computed(() => session.phase === "ready" && session.ready);

useShortcuts((id) => {
  switch (id) {
    case "close":
      if (showKeys.value) showKeys.value = false;
      closeLookup();
      return false;
    case "help":
      showKeys.value = true;
      return;
    case "search":
      if (!wide.value) tab.value = "transcript";
      setTimeout(() => transcript.value?.focusSearch(), 0);
      return;
    case "subs":
      prefs.show = !prefs.show;
      return;
    case "bilingual":
      prefs.bilingual = !prefs.bilingual;
      return;
    case "bigger":
      prefs.size = Math.min(SUB_SIZE.max, prefs.size + SUB_SIZE.step);
      return;
    case "smaller":
      prefs.size = Math.max(SUB_SIZE.min, prefs.size - SUB_SIZE.step);
      return;
    case "learn":
      prefs.learn = !prefs.learn;
      toast(prefs.learn ? t("learn.learnOn") : t("learn.learnOff"));
      return;
    case "loop":
      armLoop();
      prefs.loop = !prefs.loop;
      toast(prefs.loop ? t("learn.loopOn") : t("learn.loopOff"));
      return;
  }
  if (!ready.value) return false;
  switch (id) {
    case "play":
      togglePlay();
      return;
    case "dub":
      toggleLiveDub();
      return;
    case "fullscreen":
      stage.value?.toggleFullscreen();
      return;
    case "repeat":
      stepLine(0);
      return;
    case "next":
      stepLine(1);
      return;
    case "prev":
      stepLine(-1);
      return;
  }
});
</script>

<template>
  <div class="watch" :class="{ wide: wide && session.phase === 'ready' }">
    <div class="main">
      <div class="player-wrap">
        <PlayerStage ref="stage" />
      </div>
      <template v-if="session.phase === 'ready'">
        <PlayerToolbar @fullscreen="stage?.toggleFullscreen()" @shortcuts="showKeys = true" />
        <VideoMeta />

        <div class="tasks">
          <div class="tablist" role="tablist" :aria-label="t('watch.tasks')" @keydown="onTabKey">
            <button
              v-for="x in tabs"
              :id="'tab-' + x.id"
              :key="x.id"
              type="button"
              role="tab"
              class="tab"
              :aria-selected="tab === x.id"
              :aria-controls="'panel-' + x.id"
              :tabindex="tab === x.id ? 0 : -1"
              @click="selectTab(x.id)"
            >
              <component :is="x.icon" :size="18" />
              <span>{{ t("watch.tab." + x.id) }}</span>
              <i v-if="x.id === 'watch' && liveDub.on" class="tab__live" :aria-label="t('dub.live.on')"></i>
            </button>
          </div>

          <div v-if="!wide" v-show="tab === 'transcript'" id="panel-transcript" role="tabpanel" aria-labelledby="tab-transcript" class="tp-mobile">
            <TranscriptPanel ref="transcript" />
          </div>
          <div v-show="tab === 'watch'" id="panel-watch" role="tabpanel" aria-labelledby="tab-watch" class="panel"><WatchPanel /></div>
          <div v-show="tab === 'export'" id="panel-export" role="tabpanel" aria-labelledby="tab-export" class="panel"><ExportPanel /></div>
          <div v-show="tab === 'ask'" id="panel-ask" role="tabpanel" aria-labelledby="tab-ask" class="panel"><AskPanel /></div>
          <div v-show="tab === 'learn'" id="panel-learn" role="tabpanel" aria-labelledby="tab-learn" class="panel"><LearnPanel /></div>
        </div>
      </template>
    </div>

    <aside v-if="wide && session.phase === 'ready'" class="side">
      <TranscriptPanel ref="transcript" />
    </aside>

    <WordLookup />
    <AppDialog v-model="showKeys" :title="t('shortcuts.title')">
      <ShortcutList />
    </AppDialog>
  </div>
</template>

<style scoped>
.watch {
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--s-5) var(--s-6) calc(var(--s-10) + var(--bottom-nav-h));
}
.watch.wide {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(360px, 30vw, 460px);
  gap: var(--s-6);
  align-items: start;
}
.main {
  min-width: 0;
}
.watch:not(.wide) .main {
  max-width: 1120px;
  margin: 0 auto;
}
.side {
  position: sticky;
  top: calc(var(--header-h) + var(--s-5));
  height: calc(100dvh - var(--header-h) - var(--s-10));
  min-height: 420px;
}
.tasks {
  margin-top: var(--s-2);
}
.tablist {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--line);
  overflow-x: auto;
  scrollbar-width: none;
}
.tablist::-webkit-scrollbar {
  display: none;
}
.tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 46px;
  padding: 0 var(--s-4);
  border: 0;
  background: transparent;
  color: var(--text-2);
  font-size: var(--fs-sm);
  font-weight: 500;
  white-space: nowrap;
  border-radius: var(--r-sm) var(--r-sm) 0 0;
}
.tab:hover {
  color: var(--text);
  background: var(--surface-1);
}
.tab[aria-selected="true"] {
  color: var(--text);
}
.tab[aria-selected="true"]::after {
  content: "";
  position: absolute;
  inset-inline: 10px;
  bottom: -1px;
  height: 2px;
  border-radius: 2px;
  background: var(--accent-strong);
}
.tab[aria-selected="true"] svg {
  color: var(--accent-ink);
}
.tab__live {
  width: 7px;
  height: 7px;
  border-radius: 1px;
  transform: rotate(45deg);
  background: var(--accent-strong);
}
.panel {
  margin-top: var(--s-5);
  max-width: 760px;
}
.tp-mobile {
  margin-top: var(--s-3);
  height: min(70dvh, 640px);
}
@media (max-width: 759px) {
  .watch {
    padding: 0 0 calc(var(--s-10) + var(--bottom-nav-h));
  }
  .player-wrap {
    position: sticky;
    top: var(--header-h);
    z-index: var(--z-sticky);
    background: var(--player-ground);
  }
  .tasks {
    padding: 0 var(--s-4);
  }
  .tablist {
    margin: 0 calc(var(--s-4) * -1);
    padding: 0 var(--s-2);
  }
  .tab {
    padding: 0 var(--s-3);
  }
  .panel {
    margin-top: var(--s-4);
  }
  .tp-mobile {
    height: calc(100dvh - var(--header-h) - 56vw - var(--bottom-nav-h) - 60px);
    min-height: 360px;
  }
}
</style>
