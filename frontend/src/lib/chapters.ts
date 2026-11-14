/** A video's chapters: from its owner (YouTube description) or suggested by the AI summary. */
export interface Chapter {
  start: number;
  title: string;
  /** The title in the video's language, when `title` is a translation. */
  src?: string;
}

/** The chapter playing at time t, or -1 before the first. Chapters are sorted by start. */
export function chapterAt(chapters: readonly Chapter[], t: number): number {
  let ans = -1;
  for (let i = 0; i < chapters.length && chapters[i]!.start <= t + 0.25; i++) ans = i;
  return ans;
}

/** For the transcript: the line each chapter heading goes above (line index -> chapter index).
 *  A chapter heads the first line that starts at or after it, or the line it starts in the middle of. */
export function chapterHeads(chapters: readonly Chapter[], cues: readonly { start: number; end: number }[]): Map<number, number> {
  const out = new Map<number, number>();
  let i = 0;
  chapters.forEach((ch, k) => {
    while (i < cues.length && cues[i]!.end <= ch.start + 0.25) i++;
    if (i >= cues.length) return;
    // Two chapters before the same line: the later one is the one that line belongs to.
    out.set(i, k);
  });
  return out;
}

/** Keeps chapters that make sense for this video: sorted, inside it, at least 10 s apart, titled. */
export function cleanChapters(list: readonly Chapter[] | null | undefined, duration = 0): Chapter[] {
  const out: Chapter[] = [];
  for (const c of [...(list || [])].sort((a, b) => a.start - b.start)) {
    const title = String(c?.title || "").trim();
    const start = Math.max(0, Number(c?.start) || 0);
    if (!title || (duration && start >= duration)) continue;
    if (out.length && start - out[out.length - 1]!.start < 10) continue;
    out.push({ start, title, ...(c.src && c.src !== title ? { src: c.src } : {}) });
  }
  return out.length >= 2 ? out : [];
}
