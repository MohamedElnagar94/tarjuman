/**
 * Moving the subtitles earlier or later when they don't match the speech. The offset is in seconds:
 * positive shows each line later than its caption says, negative earlier. The dub follows the same
 * clock, so it moves with the subtitles. It is kept per video for the browser session.
 */
import { ytVideoId, isYouTube } from "./cues";

export const OFFSET_MAX = 20;
export const OFFSET_STEPS = [-0.5, -0.25, 0.25, 0.5] as const;

const round = (x: number) => Math.round(x * 100) / 100;

/** A valid offset from anything (storage, messages): a number within ±20 s, in hundredths. */
export function cleanOffset(v: unknown): number {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  const r = round(Math.max(-OFFSET_MAX, Math.min(OFFSET_MAX, n)));
  return Object.is(r, -0) ? 0 : r;
}

export function nudgeOffset(offset: number, delta: number): number {
  return cleanOffset(cleanOffset(offset) + Number(delta || 0));
}

/** The caption clock for a video time: subtitles shown 0.5 s later read the captions 0.5 s behind. */
export function captionTime(videoTime: number, offset: number): number {
  return Math.max(0, (videoTime || 0) - (offset || 0));
}

/** The video time at which a caption time is shown (seeking to a line). */
export function videoTimeFor(captionT: number, offset: number): number {
  return Math.max(0, (captionT || 0) + (offset || 0));
}

/** "+0.25", "−0.50", "0.00": the sign always shown, a true minus sign, two decimals. */
export function formatOffset(offset: number): string {
  const o = cleanOffset(offset);
  if (o === 0) return "0.00";
  return (o > 0 ? "+" : "−") + Math.abs(o).toFixed(2);
}

/** The key the offset is remembered under: the YouTube video, or the page (site and path) elsewhere. */
export function offsetKey(url: string): string {
  if (isYouTube(url)) {
    const id = ytVideoId(url);
    if (id) return "yt:" + id;
  }
  try {
    const u = new URL(url);
    return u.origin + u.pathname;
  } catch {
    return String(url || "");
  }
}

/** Keeps the most recent entries only, so the session store doesn't grow without end. */
export function rememberOffset(map: Record<string, number>, key: string, offset: number, max = 200): Record<string, number> {
  const next = { ...map };
  delete next[key];
  if (cleanOffset(offset) !== 0) next[key] = cleanOffset(offset);
  const keys = Object.keys(next);
  for (const k of keys.slice(0, Math.max(0, keys.length - max))) delete next[k];
  return next;
}
