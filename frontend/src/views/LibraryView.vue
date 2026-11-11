<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhCheckCircle, PhCircleNotch, PhDownloadSimple, PhFileText, PhFilmStrip, PhPlay, PhPlaylist, PhWarningCircle, PhX, PhXCircle } from "@phosphor-icons/vue";
import ConfirmButton from "@/components/ui/ConfirmButton.vue";
import ProgressMeter from "@/components/ui/ProgressMeter.vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import { api, errorCode } from "@/api/client";
import type { Job, LibraryItem, MediaItem } from "@/api/types";
import { errText } from "@/i18n";
import { usePrefs } from "@/composables/prefs";
import { toast } from "@/composables/toast";
import { formatSize } from "@/lib/time";

const { t, locale } = useI18n();
const route = useRoute();
const prefs = usePrefs();

const jobs = ref<Job[]>([]);
const media = ref<MediaItem[] | null>(null);
const files = ref<LibraryItem[] | null>(null);
const loadFailed = ref(false);
const playing = ref<string | null>(null);

const batchUrl = ref(String(route.query.batch || ""));
const batchWhat = ref<"subs" | "subvideo" | "dub">("subs");
const batchLimit = ref(20);
const batchBusy = ref(false);
const batchErr = ref("");

const units = computed(() => ({ kb: t("units.kb"), mb: t("units.mb"), gb: t("units.gb") }));
const size = (b: number) => formatSize(b, units.value);
const date = (ms: number) => new Date(ms).toLocaleDateString(locale.value === "ar" ? "ar" : "en", { year: "numeric", month: "short", day: "numeric" });

const active = computed(() => jobs.value.filter((j) => j.status === "running" || j.status === "queued"));
const finished = computed(() => jobs.value.filter((j) => j.status !== "running" && j.status !== "queued").slice(0, 8));
const dubbed = computed(() => (files.value || []).filter((x) => x.kind === "dubbed"));
const subs = computed(() => (files.value || []).filter((x) => x.kind === "subs"));

let timer: number | undefined;

async function loadJobs() {
  window.clearTimeout(timer);
  try {
    jobs.value = (await api.jobs()).jobs || [];
    loadFailed.value = false;
  } catch {
    loadFailed.value = true;
  }
  // Poll while something runs; refresh the files when a job has just finished.
  if (active.value.length) timer = window.setTimeout(async () => {
    const before = active.value.length;
    await loadJobs();
    if (active.value.length < before) void loadFiles();
  }, 3000);
}

async function loadFiles() {
  try {
    const [m, l] = await Promise.all([api.media(), api.library()]);
    media.value = m.items || [];
    files.value = l.items || [];
    loadFailed.value = false;
  } catch {
    media.value ??= [];
    files.value ??= [];
    loadFailed.value = true;
  }
}

onMounted(() => {
  void loadJobs();
  void loadFiles();
});
onBeforeUnmount(() => window.clearTimeout(timer));
watch(
  () => route.query.batch,
  (b) => {
    if (b) batchUrl.value = String(b);
  },
);

const whatOptions = computed(() => [
  { value: "subs" as const, label: t("library.batch.subs") },
  { value: "subvideo" as const, label: t("library.batch.subvideo") },
  { value: "dub" as const, label: t("library.batch.dub") },
]);

async function startBatch() {
  const url = batchUrl.value.trim();
  batchErr.value = "";
  if (!url) {
    batchErr.value = t("library.batch.needUrl");
    return;
  }
  batchBusy.value = true;
  try {
    await api.startBatch({
      url,
      what: batchWhat.value,
      limit: Math.max(1, Math.min(200, Number(batchLimit.value) || 20)),
      tl: prefs.tl,
      voice: prefs.voice,
      quality: prefs.quality,
      bgVolume: prefs.bgVol,
      embedSubs: prefs.embedSubs,
    });
    toast(t("library.batch.started"), { tone: "ok" });
    batchUrl.value = "";
    await loadJobs();
  } catch (e) {
    batchErr.value = errText(errorCode(e), (e as Error).message);
  } finally {
    batchBusy.value = false;
  }
}

async function cancel(id: string) {
  await api.cancelJob(id).catch(() => {});
  void loadJobs();
}

async function deleteMedia(m: MediaItem) {
  try {
    await api.deleteMedia(m.id);
    media.value = (media.value || []).filter((x) => x.id !== m.id);
    toast(t("library.deleted"));
  } catch (e) {
    toast(errText(errorCode(e)), { tone: "danger" });
  }
}

async function deleteFile(f: LibraryItem) {
  try {
    await api.deleteLibraryFile(f.kind, f.name);
    files.value = (files.value || []).filter((x) => !(x.kind === f.kind && x.name === f.name));
    toast(t("library.deleted"));
  } catch (e) {
    toast(errText(errorCode(e)), { tone: "danger" });
  }
}

const jobTitle = (j: Job) => j.title || (j.type === "batch" ? t("library.jobs.playlist") : j.videoId || j.id);
const fileKey = (f: LibraryItem) => f.kind + "/" + f.name;
const isVideo = (f: LibraryItem) => f.name.toLowerCase().endsWith(".mp4");
</script>

<template>
  <div class="page lib">
    <header class="page__head">
      <h1 class="page__title">{{ t("library.title") }}</h1>
      <p class="muted">{{ t("library.lead") }}</p>
      <nav class="jump" :aria-label="t('library.sections')">
        <a href="#jobs">{{ t("library.jobs.title") }}<span v-if="active.length" class="count">{{ active.length }}</span></a>
        <a href="#batch">{{ t("library.batch.title") }}</a>
        <a href="#media">{{ t("library.media.title") }}</a>
        <a href="#files">{{ t("library.files.title") }}</a>
      </nav>
    </header>

    <p v-if="loadFailed" class="notice notice--danger" role="alert"><PhWarningCircle :size="18" />{{ errText("NO_SERVER") }}</p>

    <div class="cols">
      <div class="col">
        <!-- jobs -->
        <section id="jobs" class="sec" aria-labelledby="h-jobs">
          <h2 id="h-jobs" class="section-title">{{ t("library.jobs.title") }}</h2>
          <div v-if="!active.length && !finished.length" class="empty">
            <strong>{{ t("library.jobs.emptyTitle") }}</strong>
            <span>{{ t("library.jobs.emptyBody") }}</span>
          </div>
          <ul v-else class="jobs">
            <li v-for="j in active" :key="j.id" class="job panel">
              <div class="job__head">
                <PhCircleNotch class="spin" :size="18" />
                <div class="job__title">
                  <strong dir="auto">{{ jobTitle(j) }}</strong>
                  <span>{{ t("library.jobs.type." + j.type) }}<template v-if="j.what"> · {{ t("library.batch." + j.what) }}</template></span>
                </div>
                <button type="button" class="btn btn--quiet btn--sm" @click="cancel(j.id)"><PhX :size="14" />{{ t("common.cancel") }}</button>
              </div>
              <ProgressMeter :value="j.progress || 0" :label="(j.phase || t('library.jobs.queued')) + ' · ' + Math.round(j.progress || 0) + '%'" />
              <ul v-if="j.items?.length" class="items">
                <li v-for="x in j.items" :key="x.id" :class="'s-' + x.status">
                  <PhCheckCircle v-if="x.status === 'done'" :size="14" />
                  <PhXCircle v-else-if="x.status === 'error'" :size="14" />
                  <PhCircleNotch v-else-if="x.status === 'running'" class="spin" :size="14" />
                  <span v-else class="dot" aria-hidden="true"></span>
                  <span dir="auto">{{ x.title }}<template v-if="x.message"> · {{ x.message }}</template></span>
                </li>
              </ul>
            </li>
            <li v-for="j in finished" :key="j.id" class="job job--done">
              <PhCheckCircle v-if="j.status === 'done'" class="ok" :size="18" />
              <PhXCircle v-else class="bad" :size="18" />
              <div class="job__title">
                <strong dir="auto">{{ jobTitle(j) }}</strong>
                <span>{{ t("library.jobs.type." + j.type) }} · {{ j.status === "done" ? t("library.jobs.done") : j.status === "cancelled" ? t("library.jobs.cancelled") : errText(j.message, j.message) }}</span>
              </div>
              <a v-if="j.status === 'done' && j.fileUrl" class="btn btn--quiet btn--sm" :href="api.dubFileUrl(j.id, true)" :download="j.fileName"><PhDownloadSimple :size="16" />{{ t("common.download") }}</a>
            </li>
          </ul>
        </section>

        <!-- batch -->
        <section id="batch" class="sec panel" aria-labelledby="h-batch">
          <h2 id="h-batch" class="panel__title"><PhPlaylist :size="20" />{{ t("library.batch.title") }}</h2>
          <p class="panel__lead">{{ t("library.batch.lead") }}</p>
          <p v-if="route.query.kind" class="notice notice--accent batch-hint">{{ route.query.kind === "channel" ? t("library.batch.fromChannel") : t("library.batch.fromPlaylist") }}</p>
          <form class="form" @submit.prevent="startBatch">
            <div class="field">
              <label for="b-url">{{ t("library.batch.url") }}</label>
              <input id="b-url" v-model="batchUrl" class="input ltr" type="url" inputmode="url" placeholder="https://www.youtube.com/playlist?list=…" autocomplete="off" :aria-invalid="!!batchErr" />
              <span v-if="batchErr" class="field__error" role="alert">{{ batchErr }}</span>
            </div>
            <div class="field">
              <span class="field__label">{{ t("library.batch.what") }}</span>
              <SegmentedControl v-model="batchWhat" :options="whatOptions" :label="t('library.batch.what')" block />
            </div>
            <div class="field narrow">
              <label for="b-limit">{{ t("library.batch.limit") }}</label>
              <input id="b-limit" v-model.number="batchLimit" class="input" type="number" min="1" max="200" />
              <span class="field__help">{{ t("library.batch.uses", { lang: t("langs." + prefs.tl), quality: prefs.quality }) }}</span>
            </div>
            <div>
              <button class="btn btn--primary" type="submit" :disabled="batchBusy">{{ t("library.batch.start") }}</button>
            </div>
          </form>
        </section>
      </div>

      <div class="col">
        <!-- uploaded and downloaded media -->
        <section id="media" class="sec" aria-labelledby="h-media">
          <div class="sec__head">
            <h2 id="h-media" class="section-title">{{ t("library.media.title") }}</h2>
            <RouterLink to="/" class="btn btn--outline btn--sm">{{ t("library.media.add") }}</RouterLink>
          </div>
          <div v-if="media === null" class="list" aria-busy="true">
            <div v-for="n in 2" :key="n" class="skeleton sk"></div>
          </div>
          <div v-else-if="!media.length" class="empty">
            <strong>{{ t("library.media.emptyTitle") }}</strong>
            <span>{{ t("library.media.emptyBody") }}</span>
          </div>
          <ul v-else class="list">
            <li v-for="m in media" :key="m.id" class="item">
              <span class="item__icon"><PhFilmStrip :size="18" /></span>
              <div class="item__txt">
                <strong dir="auto">{{ m.title }}</strong>
                <span>{{ size(m.size) }} · {{ m.transcribed ? t("library.media.transcribed") : t("library.media.notTranscribed") }}</span>
              </div>
              <div class="item__ops">
                <RouterLink :to="{ name: 'watch', query: { url: m.link } }" class="btn btn--outline btn--sm"><PhPlay :size="14" />{{ t("common.open") }}</RouterLink>
                <ConfirmButton icon :label="t('common.delete')" :confirm-label="t('common.confirmDelete')" @confirm="deleteMedia(m)" />
              </div>
            </li>
          </ul>
        </section>

        <!-- output files -->
        <section id="files" class="sec" aria-labelledby="h-files">
          <h2 id="h-files" class="section-title">{{ t("library.files.title") }}</h2>
          <h3 class="sub-h">{{ t("library.files.dubbed") }}</h3>
          <div v-if="files !== null && !dubbed.length" class="empty small">{{ t("library.files.dubbedEmpty") }}</div>
          <ul v-else class="list">
            <li v-for="f in dubbed" :key="fileKey(f)" class="item" :class="{ open: playing === fileKey(f) }">
              <span class="item__icon accent"><PhFilmStrip :size="18" /></span>
              <div class="item__txt">
                <strong dir="auto">{{ f.name }}</strong>
                <span>{{ size(f.size) }} · {{ date(f.mtime) }}</span>
              </div>
              <div class="item__ops">
                <button v-if="isVideo(f)" type="button" class="btn btn--outline btn--sm" :aria-pressed="playing === fileKey(f)" @click="playing = playing === fileKey(f) ? null : fileKey(f)"><PhPlay :size="14" />{{ t("library.files.play") }}</button>
                <a class="btn btn--quiet btn--icon btn--sm" :href="api.libraryFileUrl(f.kind, f.name, true)" :download="f.name" :aria-label="t('common.download')"><PhDownloadSimple :size="16" /></a>
                <ConfirmButton icon :label="t('common.delete')" :confirm-label="t('common.confirmDelete')" @confirm="deleteFile(f)" />
              </div>
              <video v-if="playing === fileKey(f)" class="item__video" :src="api.libraryFileUrl(f.kind, f.name)" controls autoplay></video>
            </li>
          </ul>
          <h3 class="sub-h">{{ t("library.files.subs") }}</h3>
          <div v-if="files !== null && !subs.length" class="empty small">{{ t("library.files.subsEmpty") }}</div>
          <ul v-else class="list">
            <li v-for="f in subs" :key="fileKey(f)" class="item">
              <span class="item__icon"><PhFileText :size="18" /></span>
              <div class="item__txt">
                <strong dir="auto">{{ f.name }}</strong>
                <span>{{ size(f.size) }} · {{ date(f.mtime) }}</span>
              </div>
              <div class="item__ops">
                <a class="btn btn--quiet btn--icon btn--sm" :href="api.libraryFileUrl(f.kind, f.name, true)" :download="f.name" :aria-label="t('common.download')"><PhDownloadSimple :size="16" /></a>
                <ConfirmButton icon :label="t('common.delete')" :confirm-label="t('common.confirmDelete')" @confirm="deleteFile(f)" />
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.jump {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: var(--s-3);
}
.jump a {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  border-radius: var(--r-pill);
  border: 1px solid var(--line-2);
  color: var(--text-2);
  text-decoration: none;
  font-size: var(--fs-xs);
}
.jump a:hover {
  color: var(--text);
  background: var(--surface-1);
}
.count {
  display: grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--accent);
  color: var(--on-accent);
  font-size: 11px;
  font-weight: 700;
}
.cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: var(--s-8);
  align-items: start;
}
.col {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--s-8);
  min-width: 0;
}
.sec {
  scroll-margin-top: calc(var(--header-h) + 16px);
}
.sec > .section-title,
.sec__head {
  margin-bottom: var(--s-4);
}
.sec__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
}
.sec__head .section-title {
  margin: 0;
}
.jobs {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--s-3);
}
.job.panel {
  display: grid;
  gap: var(--s-3);
  padding: var(--s-4);
}
.job__head {
  display: flex;
  align-items: center;
  gap: var(--s-3);
}
.job__head .spin {
  color: var(--accent-ink);
}
.job__title {
  flex: 1;
  min-width: 0;
  display: grid;
  font-size: var(--fs-sm);
}
.job__title strong {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.job__title span {
  color: var(--text-2);
  font-size: var(--fs-xs);
}
.job--done {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-2) var(--s-1);
  border-top: 1px solid var(--line);
}
.ok {
  color: var(--ok);
}
.bad {
  color: var(--danger);
}
.items {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 200px;
  overflow-y: auto;
  display: grid;
  gap: 4px;
  font-size: var(--fs-xs);
  color: var(--text-2);
}
.items li {
  display: flex;
  align-items: center;
  gap: 8px;
}
.items .s-done svg {
  color: var(--ok);
}
.items .s-error {
  color: var(--danger);
}
.items .s-running svg {
  color: var(--accent-ink);
}
.dot {
  width: 6px;
  height: 6px;
  margin: 0 4px;
  border-radius: 1px;
  transform: rotate(45deg);
  background: var(--text-3);
}
.spin {
  animation: spin 1.1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.form {
  display: grid;
  gap: var(--s-4);
  margin-top: var(--s-4);
}
.narrow .input {
  max-width: 140px;
}
.batch-hint {
  margin-top: var(--s-3);
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
}
.sk {
  height: 56px;
  margin-bottom: 8px;
}
.item {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  gap: var(--s-3);
  align-items: center;
  padding: var(--s-3) 0;
  border-top: 1px solid var(--line);
}
.item:first-child {
  border-top: 0;
}
.item__icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--r-sm);
  background: var(--lapis-soft);
  color: var(--lapis);
}
.item__icon.accent {
  background: var(--accent-soft);
  color: var(--accent-ink);
}
.item__txt {
  display: grid;
  min-width: 0;
  font-size: var(--fs-sm);
}
.item__txt strong {
  font-weight: 500;
  overflow-wrap: anywhere;
}
.item__txt span {
  color: var(--text-2);
  font-size: var(--fs-xs);
}
.item__ops {
  display: flex;
  align-items: center;
  gap: 2px;
}
.item__video {
  grid-column: 1 / -1;
  width: 100%;
  border-radius: var(--r-md);
  background: var(--player-ground);
}
.sub-h {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-2);
  margin: var(--s-4) 0 var(--s-2);
}
.empty.small {
  padding: var(--s-4);
}
.notice {
  margin-bottom: var(--s-6);
}
@media (max-width: 1023px) {
  .cols {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 480px) {
  .item {
    grid-template-columns: 36px minmax(0, 1fr);
  }
  .item__ops {
    grid-column: 2;
  }
}
</style>
