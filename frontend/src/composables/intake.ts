/* Getting a video in: a pasted link (YouTube, playlist, channel, any site) or a file from this device. */
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { api, errorCode } from "@/api/client";
import { errText, i18n } from "@/i18n";
import { classifyLink } from "@/lib/links";
import { pollJob } from "./jobs";

export const intake = reactive({
  busy: false,
  kind: "" as "" | "upload" | "fetch",
  label: "",
  progress: 0,
  error: "",
});

let abortUpload: (() => void) | null = null;
let stopFetch: (() => void) | null = null;

export function useIntake() {
  const router = useRouter();
  const t = i18n.global.t;

  function reset() {
    Object.assign(intake, { busy: false, kind: "", label: "", progress: 0 });
  }

  async function openLink(input: string): Promise<boolean> {
    intake.error = "";
    const { kind, link } = classifyLink(input);
    switch (kind) {
      case "youtube":
      case "media":
        await router.push({ name: "watch", query: { url: link } });
        return true;
      case "playlist":
      case "channel":
        await router.push({ name: "library", query: { batch: link, kind } });
        return true;
      case "site":
        return fetchFromSite(link);
      default:
        intake.error = input.trim() ? t("intake.invalid") : t("intake.empty");
        return false;
    }
  }

  async function fetchFromSite(link: string): Promise<boolean> {
    Object.assign(intake, { busy: true, kind: "fetch", label: t("intake.fetching", { pct: 0 }), progress: 0, error: "" });
    try {
      const { id } = await api.fetchMedia(link);
      const poll = pollJob(
        () => api.mediaJob(id),
        (j) => {
          intake.progress = j.progress || 0;
          intake.label = t("intake.fetching", { pct: Math.round(j.progress || 0) });
        },
        { interval: 1200 },
      );
      stopFetch = () => {
        poll.stop();
        api.cancelJob(id).catch(() => {});
      };
      const j = await poll.done;
      reset();
      if (j.status === "done" && j.media) {
        await router.push({ name: "watch", query: { url: j.media.link } });
        return true;
      }
      if (j.status !== "cancelled") intake.error = j.message ? errText(j.message, j.message) : t("intake.fetchFailed");
      return false;
    } catch (e) {
      reset();
      intake.error = errText(errorCode(e), (e as Error).message);
      return false;
    }
  }

  async function upload(file: File | null | undefined): Promise<boolean> {
    if (!file) return false;
    Object.assign(intake, { busy: true, kind: "upload", label: t("intake.uploading", { name: file.name, pct: 0 }), progress: 0, error: "" });
    const req = api.upload(file, (f) => {
      intake.progress = f * 100;
      intake.label = t("intake.uploading", { name: file.name, pct: Math.round(f * 100) });
    });
    abortUpload = req.abort;
    try {
      const item = await req.promise;
      reset();
      await router.push({ name: "watch", query: { url: item.link } });
      return true;
    } catch (e) {
      reset();
      const code = errorCode(e);
      if (code !== "CANCELLED") intake.error = errText(code, (e as Error).message);
      return false;
    } finally {
      abortUpload = null;
    }
  }

  function cancel() {
    abortUpload?.();
    stopFetch?.();
    stopFetch = null;
    reset();
  }

  return { intake, openLink, upload, cancel };
}
