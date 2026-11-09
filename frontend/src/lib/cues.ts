import type { Cue } from "@/api/types";

/** Index of the cue showing at time t (binary search on start), or -1 between cues. */
export function activeIndex(cues: readonly Pick<Cue, "start" | "end">[], t: number): number {
  let lo = 0;
  let hi = cues.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (cues[mid]!.start <= t) {
      ans = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans >= 0 && t < cues[ans]!.end ? ans : -1;
}

/** Last cue that has started by t (50 ms tolerance), -1 before the first. Used by next/previous line. */
export function lastStartedIndex(cues: readonly Pick<Cue, "start">[], t: number): number {
  let lo = 0;
  let hi = cues.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (cues[mid]!.start <= t + 0.05) {
      ans = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return ans;
}

/** Translation order: the lines nearest the playhead first, so what you are watching gets translated first. */
export function translationOrder(
  cues: readonly Pick<Cue, "start" | "src">[],
  skip: (i: number) => boolean,
  t: number,
  max = 40,
): number[] {
  const todo: number[] = [];
  for (let i = 0; i < cues.length; i++) if (cues[i]!.src && !skip(i)) todo.push(i);
  todo.sort((a, b) => Math.abs(cues[a]!.start - t) - Math.abs(cues[b]!.start - t));
  return todo.slice(0, max);
}

export type SubTextMode = "ar" | "bi" | "src";

/** The transcript as plain text, the way "copy" puts it on the clipboard. */
export function transcriptText(
  cues: readonly Pick<Cue, "start" | "src">[],
  tr: (i: number) => string,
  mode: SubTextMode,
  fmt: (t: number) => string,
): string {
  return cues
    .map((c, i) => {
      const t = tr(i) || "";
      const body = mode === "src" ? c.src : mode === "bi" ? [c.src, t].filter(Boolean).join("\n") : t || c.src;
      return fmt(c.start) + "  " + body;
    })
    .join(mode === "bi" ? "\n\n" : "\n");
}
