import { ApiError } from "@/api/client";
import type { Job } from "@/api/types";

export interface JobPoll<T> {
  stop(): void;
  /** Resolves with the final job, or rejects with an ApiError (NO_JOB when the server forgot it). */
  done: Promise<T>;
}

const FINAL = new Set(["done", "error", "cancelled"]);

/** Polls a job until it finishes. Network blips are retried; the server losing the job is not. */
export function pollJob<T extends Pick<Job, "status">>(
  fetchJob: () => Promise<T>,
  onUpdate: (job: T) => void,
  opts: { interval?: number; retry?: number } = {},
): JobPoll<T> {
  let stopped = false;
  let timer: number | undefined;
  const interval = opts.interval ?? 1500;
  const retry = opts.retry ?? 2500;
  const done = new Promise<T>((resolve, reject) => {
    const tick = async () => {
      if (stopped) return;
      let job: T;
      try {
        job = await fetchJob();
      } catch (e) {
        if (stopped) return;
        if (e instanceof ApiError && e.code !== "NO_SERVER") return reject(e);
        timer = window.setTimeout(tick, retry);
        return;
      }
      if (stopped) return;
      onUpdate(job);
      if (FINAL.has(job.status)) return resolve(job);
      timer = window.setTimeout(tick, interval);
    };
    void tick();
  });
  return {
    stop() {
      stopped = true;
      window.clearTimeout(timer);
    },
    done,
  };
}

/** Desktop notification when a long job finishes while the tab is in the background. */
export function notifyDone(title: string, body: string): void {
  try {
    if (document.hidden && "Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body, icon: "/favicon.svg" });
    }
  } catch {
    /* notifications unsupported */
  }
}

export function askNotificationPermission(): void {
  try {
    if ("Notification" in window && Notification.permission === "default") void Notification.requestPermission().catch(() => {});
  } catch {
    /* unsupported */
  }
}
