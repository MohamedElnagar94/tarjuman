<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { PhCopy, PhDownloadSimple, PhFilmSlate, PhMicrophoneStage, PhWarningCircle, PhX } from "@phosphor-icons/vue";
import ProgressMeter from "@/components/ui/ProgressMeter.vue";
import SegmentedControl from "@/components/ui/SegmentedControl.vue";
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue";
import { api, errorCode } from "@/api/client";
import type { Quality, SubFormat, SubMode } from "@/api/types";
import { errText } from "@/i18n";
import { usePrefs } from "@/composables/prefs";
import { cues, session, tr } from "@/composables/session";
import { toast } from "@/composables/toast";
import { cancelVideoJob, startDubJob, startSubVideoJob, videoJobs } from "@/composables/videoJobs";
import { useVoices } from "@/composables/voices";
import { transcriptText } from "@/lib/cues";
import { formatSize, formatTime } from "@/lib/time";

const { t } = useI18n();
const prefs = usePrefs();
const { voices } = useVoices();
const downloading = ref(false);

const modeOptions = computed(() => [
  { value: "ar" as SubMode, label: t("export.mode.ar") },
  { value: "bi" as SubMode, label: t("export.mode.bi") },
  { value: "src" as SubMode, label: t("export.mode.src") },
]);
const fmtOptions = computed(() => [
  { value: "srt" as SubFormat, label: "SRT" },
  { value: "vtt" as SubFormat, label: "VTT" },
  { value: "txt" as SubFormat, label: t("export.fmt.txt") },
]);
const qualityOptions = [480, 720, 1080].map((q) => ({ value: q as Quality, label: q + "p" }));
const units = computed(() => ({ kb: t("units.kb"), mb: t("units.mb"), gb: t("units.gb") }));

function saveBlob(blob: Blob, name: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

async function download() {
  downloading.value = true;
  try {
    const r = await api.downloadSubs(session.link, session.tl, prefs.dlMode, prefs.dlFmt);
    saveBlob(r.blob, r.fileName || "subtitles." + prefs.dlFmt);
    toast(t("export.subs.done"), { tone: "ok" });
  } catch (e) {
    toast(errText(errorCode(e), (e as Error).message), { tone: "danger" });
  } finally {
    downloading.value = false;
  }
}

async function copy() {
  const text = transcriptText(cues.value, (i) => tr.value[i] || "", prefs.dlMode, formatTime);
  try {
    await navigator.clipboard.writeText(text);
    toast(t("export.subs.copied"), { tone: "ok" });
  } catch {
    toast(t("export.subs.copyBlocked"), { tone: "danger" });
  }
}

function resultMeta(kind: "dub" | "subvideo") {
  const j = videoJobs[kind].result;
  if (!j) return "";
  const bits = [formatSize(j.size, units.value)];
  const info = j.dubInfo || {};
  const n = info.sentences || info.placed;
  if (n) bits.push(t("export.dub.sentences", { n }));
  const v = voices.value.find((x) => x.id === info.voice);
  if (v) bits.push(t("export.dub.voice", { name: v.name }));
  if (info.refit) bits.push(t("export.dub.refit", { n: info.refit }));
  if (info.voiceRemoved) bits.push(t("export.dub.voiceRemoved"));
  if (info.multiSpeaker) bits.push(t("export.dub.multiSpeaker"));
  return bits.join(t("common.listSep"));
}
const fileUrl = (kind: "dub" | "subvideo") => videoJobs[kind].result?.fileUrl || api.dubFileUrl(videoJobs[kind].id);
const dlUrl = (kind: "dub" | "subvideo") => api.dubFileUrl(videoJobs[kind].id, true);
</script>

<template>
  <div class="task-stack">
    <section class="task" aria-labelledby="g-file">
      <h3 id="g-file" class="task__title">{{ t("export.subs.title") }}</h3>
      <div class="opt">
        <span class="opt__label">{{ t("export.mode.label") }}</span>
        <SegmentedControl v-model="prefs.dlMode" :options="modeOptions" :label="t('export.mode.label')" size="sm" />
      </div>
      <div class="opt">
        <span class="opt__label">{{ t("export.fmt.label") }}<small>{{ t("export.fmt.hint") }}</small></span>
        <SegmentedControl v-model="prefs.dlFmt" :options="fmtOptions" :label="t('export.fmt.label')" size="sm" />
      </div>
      <div class="actions">
        <button type="button" class="btn btn--primary" :disabled="downloading || !session.link" @click="download">
          <PhDownloadSimple :size="18" />
          {{ downloading ? t("export.subs.preparing") : t("export.subs.download") }}
        </button>
        <button type="button" class="btn btn--outline" :disabled="!cues.length" @click="copy"><PhCopy :size="18" />{{ t("export.subs.copy") }}</button>
      </div>
    </section>

    <section class="task" aria-labelledby="g-mp4">
      <h3 id="g-mp4" class="task__title">{{ session.audioOnly ? t("export.audio.title") : t("export.mp4.title") }}</h3>
      <p class="task__lead">{{ session.audioOnly ? t("export.audio.lead") : t("export.mp4.lead") }}</p>
      <div v-if="!session.audioOnly" class="opt">
        <span class="opt__label">{{ t("export.quality") }}<small>{{ t("export.qualityHint") }}</small></span>
        <SegmentedControl v-model="prefs.quality" :options="qualityOptions" :label="t('export.quality')" size="sm" />
      </div>

      <!-- subtitled MP4 -->
      <div class="sub">
        <div class="sub__head">
          <PhFilmSlate :size="20" />
          <div>
            <h4>{{ session.audioOnly ? t("export.audio.waveTitle") : t("export.subvideo.title") }}</h4>
            <p>{{ session.audioOnly ? t("export.audio.waveLead") : t("export.subvideo.lead") }}</p>
          </div>
        </div>
        <div v-if="videoJobs.subvideo.running" class="job">
          <ProgressMeter :value="videoJobs.subvideo.progress" :label="(videoJobs.subvideo.phase || t('export.working')) + ' · ' + Math.round(videoJobs.subvideo.progress) + '%'" />
          <button type="button" class="btn btn--quiet btn--sm" @click="cancelVideoJob('subvideo')"><PhX :size="14" />{{ t("common.cancel") }}</button>
        </div>
        <div v-else class="actions">
          <button type="button" class="btn btn--outline" :disabled="!session.link" @click="startSubVideoJob">{{ t("export.subvideo.start") }}</button>
          <a v-if="videoJobs.subvideo.result" class="btn btn--primary" :href="dlUrl('subvideo')" :download="videoJobs.subvideo.result.fileName"><PhDownloadSimple :size="18" />{{ t("export.downloadMp4") }}</a>
        </div>
        <p v-if="videoJobs.subvideo.error" class="notice notice--danger" role="alert"><PhWarningCircle :size="18" />{{ videoJobs.subvideo.error }}</p>
      </div>

      <!-- dubbed MP4 -->
      <div class="sub">
        <div class="sub__head">
          <PhMicrophoneStage :size="20" />
          <div>
            <h4>{{ session.audioOnly ? t("export.audio.dubTitle") : t("export.dub.title") }}</h4>
            <p>{{ session.audioOnly ? t("export.audio.dubLead") : t("export.dub.lead") }}</p>
          </div>
        </div>
        <div v-if="!session.audioOnly" class="opt">
          <label class="opt__label" for="x-embed">{{ t("export.dub.embed") }}<small>{{ t("export.dub.embedHint") }}</small></label>
          <ToggleSwitch id="x-embed" v-model="prefs.embedSubs" />
        </div>
        <div v-if="!session.audioOnly" class="opt">
          <label class="opt__label" for="x-remove">{{ t("export.dub.remove") }}<small>{{ t("export.dub.removeHint") }}</small></label>
          <ToggleSwitch id="x-remove" v-model="prefs.removeVoice" />
        </div>
        <div v-if="!session.audioOnly" class="opt">
          <label class="opt__label" for="x-burn">{{ t("export.dub.burn") }}<small>{{ t("export.dub.burnHint") }}</small></label>
          <ToggleSwitch id="x-burn" v-model="prefs.burnSubs" />
        </div>
        <div class="opt">
          <label class="opt__label" for="x-bg">{{ t("dub.bg.label") }}<small>{{ prefs.bgVol > 0 ? t("dub.bg.level", { pct: Math.round(prefs.bgVol * 100) }) : t("dub.bg.muted") }}</small></label>
          <input id="x-bg" v-model.number="prefs.bgVol" class="range" type="range" min="0" max="0.5" step="0.02" />
        </div>
        <div v-if="videoJobs.dub.running" class="job">
          <ProgressMeter :value="videoJobs.dub.progress" :label="(videoJobs.dub.phase || t('export.working')) + ' · ' + Math.round(videoJobs.dub.progress) + '%'" />
          <button type="button" class="btn btn--quiet btn--sm" @click="cancelVideoJob('dub')"><PhX :size="14" />{{ t("common.cancel") }}</button>
        </div>
        <div v-else class="actions">
          <button type="button" class="btn btn--primary" :disabled="!session.link" @click="startDubJob"><PhMicrophoneStage :size="18" />{{ t("export.dub.start") }}</button>
        </div>
        <p v-if="videoJobs.dub.error" class="notice notice--danger" role="alert"><PhWarningCircle :size="18" />{{ videoJobs.dub.error }}</p>
        <div v-if="videoJobs.dub.result && !videoJobs.dub.running" class="result">
          <audio v-if="videoJobs.dub.result.fileName.endsWith('.m4a')" :src="fileUrl('dub')" controls preload="metadata"></audio>
          <video v-else :src="fileUrl('dub')" controls preload="metadata"></video>
          <p class="result__meta">{{ resultMeta("dub") }}</p>
          <div class="actions">
            <a class="btn btn--primary" :href="dlUrl('dub')" :download="videoJobs.dub.result.fileName"><PhDownloadSimple :size="18" />{{ videoJobs.dub.result.fileName.endsWith(".m4a") ? t("export.audio.download") : t("export.downloadMp4") }}</a>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.sub {
  margin-top: var(--s-4);
  padding: var(--s-4);
  border-radius: var(--r-md);
  background: var(--bg);
  border: 1px solid var(--line);
}
.sub__head {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: var(--s-3);
  margin-bottom: var(--s-2);
}
.sub__head svg {
  color: var(--accent-ink);
  margin-top: 3px;
}
.sub__head h4 {
  font-size: var(--fs-sm);
  font-weight: 600;
}
.sub__head p {
  font-size: var(--fs-xs);
  color: var(--text-2);
}
.range {
  width: 150px;
}
.notice {
  margin-top: var(--s-3);
}
</style>
