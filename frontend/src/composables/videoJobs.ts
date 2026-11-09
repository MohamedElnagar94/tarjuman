/* The MP4 jobs of the video being watched: dubbed MP4 and subtitled MP4. */
import { reactive } from "vue";
import { api, errorCode } from "@/api/client";
import type { Job } from "@/api/types";
import { errText, i18n } from "@/i18n";
import { askNotificationPermission, notifyDone, pollJob, type JobPoll } from "./jobs";
import { usePrefs } from "./prefs";
import { session } from "./session";
import { toast } from "./toast";

type Kind = "dub" | "subvideo";

interface Slot {
  id: string;
  running: boolean;
  progress: number;
  phase: string;
  error: string;
  result: Job | null;
}

const blank = (): Slot => ({ id: "", running: false, progress: 0, phase: "", error: "", result: null });

export const videoJobs = reactive<Record<Kind, Slot>>({ dub: blank(), subvideo: blank() });
const polls: Partial<Record<Kind, JobPoll<Job>>> = {};
const t = (k: string, p?: Record<string, unknown>) => i18n.global.t(k, p ?? {});

function follow(kind: Kind, id: string): void {
  polls[kind]?.stop();
  const slot = videoJobs[kind];
  Object.assign(slot, { id, running: true, progress: 0, phase: "", error: "", result: null });
  const videoId = session.videoId;
  const poll = pollJob(
    () => api.dubJob(id),
    (j) => {
      if (slot.id !== id) return;
      slot.progress = j.progress || 0;
      slot.phase = j.phase || "";
    },
  );
  polls[kind] = poll;
  poll.done
    .then((j) => {
      if (slot.id !== id) return;
      slot.running = false;
      if (j.status === "done") {
        slot.result = j;
        const msg = kind === "dub" ? t("export.dub.ready") : t("export.subvideo.ready");
        if (session.videoId === videoId) toast(msg, { tone: "ok" });
        notifyDone(msg, j.title || "");
      } else if (j.status === "error") {
        slot.error = errText(j.message, j.message, true);
      } else {
        slot.error = t("export.cancelled");
      }
    })
    .catch((e) => {
      if (slot.id !== id) return;
      slot.running = false;
      slot.error = errText(errorCode(e));
    });
}

export async function startDubJob(): Promise<void> {
  const p = usePrefs();
  askNotificationPermission();
  try {
    const { id } = await api.startDub({
      url: session.link,
      lang: session.tl,
      voice: p.voice,
      bgVolume: p.bgVol,
      embedSubs: p.embedSubs,
      burnSubs: p.burnSubs,
      removeVoice: p.removeVoice,
      quality: p.quality,
    });
    follow("dub", id);
  } catch (e) {
    videoJobs.dub.error = errText(errorCode(e), (e as Error).message);
  }
}

export async function startSubVideoJob(): Promise<void> {
  const p = usePrefs();
  askNotificationPermission();
  try {
    const { id } = await api.startSubVideo({ url: session.link, tl: session.tl, mode: p.dlMode === "bi" ? "bi" : "ar", quality: p.quality });
    follow("subvideo", id);
  } catch (e) {
    videoJobs.subvideo.error = errText(errorCode(e), (e as Error).message);
  }
}

export function cancelVideoJob(kind: Kind): void {
  const id = videoJobs[kind].id;
  if (id) api.cancelJob(id).catch(() => {});
}

/** After a reload, pick up a running job for this video, or show the last finished one. */
export async function resumeVideoJobs(videoId: string): Promise<void> {
  for (const k of ["dub", "subvideo"] as Kind[]) {
    polls[k]?.stop();
    Object.assign(videoJobs[k], blank());
  }
  let jobs: Job[] = [];
  try {
    jobs = (await api.jobs()).jobs || [];
  } catch {
    return;
  }
  if (session.videoId !== videoId) return;
  for (const k of ["dub", "subvideo"] as Kind[]) {
    const mine = jobs.filter((j) => j.type === k && j.videoId === videoId);
    const live = mine.find((j) => j.status === "running" || j.status === "queued");
    if (live) follow(k, live.id);
    else {
      const done = mine.find((j) => j.status === "done" && j.fileUrl);
      if (done) Object.assign(videoJobs[k], { id: done.id, result: done });
    }
  }
}
