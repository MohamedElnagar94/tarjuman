export interface Cue {
  start: number;
  end: number;
  src: string;
  ar?: string;
}

/** Index of the cue showing at time t (binary search; cues sorted by start), or -1. */
export function cueIndexAt(cues: readonly Cue[], t: number): number {
  let lo = 0;
  let hi = cues.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (cues[m].start <= t) {
      ans = m;
      lo = m + 1;
    } else hi = m - 1;
  }
  return ans >= 0 && t < cues[ans].end ? ans : -1;
}

export function ytVideoId(url: string): string {
  const m = String(url).match(/(?:[?&]v=|\/shorts\/|\/embed\/|\/live\/|youtu\.be\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : "";
}

export function isYouTube(url: string | undefined | null): boolean {
  try {
    const u = new URL(String(url));
    return /(^|\.)youtube\.com$/.test(u.hostname) || /(^|\.)youtu\.be$/.test(u.hostname);
  } catch {
    return false;
  }
}

/** Pages no extension may script: browser UI, extension stores, other extensions. */
export function isProtectedUrl(url: string | undefined | null): boolean {
  const s = String(url || "");
  if (!s) return true;
  if (/^(chrome|edge|about|chrome-extension|extension|moz-extension|devtools|view-source|chrome-search|chrome-untrusted|brave|opera|vivaldi):/i.test(s)) return true;
  return /^https:\/\/(chrome\.google\.com\/webstore|chromewebstore\.google\.com|microsoftedge\.microsoft\.com\/addons)/i.test(s);
}

/** Host permission pattern for a page's origin ("https://www.coursera.org/*"), or null. */
export function originPattern(url: string | undefined | null): string | null {
  try {
    const u = new URL(String(url));
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    return `${u.protocol}//${u.hostname}/*`;
  } catch {
    return null;
  }
}

/** Text of a site's VTT cue, without markup and extra whitespace. */
export function cleanCueText(text: string): string {
  return String(text || "")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

export function normalizeTrackCues(raw: ArrayLike<{ startTime: number; endTime: number; text?: string }>): Cue[] {
  return Array.from(raw)
    .map((c) => ({ start: c.startTime, end: c.endTime, src: cleanCueText(c.text || ""), ar: "" }))
    .filter((c) => c.src && c.end > c.start)
    .sort((a, b) => a.start - b.start);
}

export interface TrackInfo {
  index: number;
  lang: string;
  label: string;
}

/** English first (best translation quality), else anything not already in the target language. */
export function pickTrack(tracks: readonly TrackInfo[], targetLang: string): TrackInfo | null {
  if (!tracks.length) return null;
  return tracks.find((t) => t.lang.startsWith("en")) || tracks.find((t) => !t.lang.startsWith(targetLang)) || tracks[0];
}

/** Index of the last cue that has started by time t (the one being said, or the one just said), or -1. */
export function lastStartedIndex(cues: readonly Cue[], t: number): number {
  let lo = 0;
  let hi = cues.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (cues[m].start <= t) {
      ans = m;
      lo = m + 1;
    } else hi = m - 1;
  }
  return ans;
}

/** The line to jump to for "previous" (-1), "repeat" (0) or "next" (1), as in the web app. -1 when there are no lines. */
export function stepLine(cues: readonly Cue[], t: number, delta: -1 | 0 | 1): number {
  if (!cues.length) return -1;
  const cur = lastStartedIndex(cues, t);
  // Before the first line, "repeat" and "next" both go to it.
  if (cur < 0) return 0;
  return Math.min(cues.length - 1, Math.max(0, cur + delta));
}
