import { DEFAULT_FONT, FONTS, type FontId } from "@/lib/fonts";
import { reactive, watch } from "vue";
import type { Quality, SubFormat, SubMode } from "@/api/types";
import { load, save } from "@/lib/storage";

export type ThemePref = "system" | "light" | "dark";
export type UiLang = "ar" | "en";

/** Everything the app remembers on this device. Defaults follow the prototype. */
export interface Prefs {
  // subtitles on the video
  show: boolean;
  bilingual: boolean;
  size: number;
  /** Subtitle font (lib/fonts.ts). */
  font: FontId;
  position: "bottom" | "top";
  bgo: number;
  tl: string;
  // transcript and learning
  follow: boolean;
  /** Transcript: both lines, the translation only, or the original only. */
  tView: "both" | "tr" | "src";
  tDensity: "cozy" | "compact";
  /** Transcript text size (px). */
  tSize: number;
  tTimes: boolean;
  /** Mark speaker changes (">>" in YouTube captions) instead of showing the symbols. */
  tTurns: boolean;
  /** Sound tags ("[Music]") as small icons. */
  tTags: boolean;
  /** The line being said fills as it is spoken, and its words light up in turn. */
  karaoke: boolean;
  // around the video
  /** Soft light around the player in the video's colours. */
  glow: boolean;
  /** The timeline under the video: where people speak, what is translated, a preview on hover. */
  timeline: boolean;
  /** Dim everything but the video. */
  cinema: boolean;
  learn: boolean;
  loop: boolean;
  quiz: boolean;
  speed: number;
  // export
  dlMode: SubMode;
  dlFmt: SubFormat;
  // dubbing
  voice: string;
  bgVol: number;
  dubWait: boolean;
  embedSubs: boolean;
  burnSubs: boolean;
  removeVoice: boolean;
  liveDub: boolean;
  quality: Quality;
  // app
  theme: ThemePref;
  uiLang: UiLang;
}

export const DEFAULT_PREFS: Prefs = {
  show: true,
  bilingual: false,
  size: 26,
  font: DEFAULT_FONT,
  position: "bottom",
  bgo: 0.78,
  tl: "ar",
  follow: true,
  tView: "both",
  tDensity: "cozy",
  tSize: 15,
  tTimes: true,
  tTurns: true,
  tTags: true,
  karaoke: true,
  glow: true,
  timeline: true,
  cinema: false,
  learn: false,
  loop: false,
  quiz: false,
  speed: 1,
  dlMode: "ar",
  dlFmt: "srt",
  voice: "auto",
  bgVol: 0.15,
  dubWait: true,
  embedSubs: true,
  burnSubs: false,
  removeVoice: true,
  liveDub: false,
  quality: 720,
  theme: "system",
  uiLang: "ar",
};

export const SUB_SIZE = { min: 14, max: 52, step: 2 } as const;
export const T_SIZE = { min: 12, max: 22, step: 1 } as const;

/** Values from storage are untrusted: coerce them back to the expected types. */
export function sanitizePrefs(raw: unknown): Prefs {
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const out: Prefs = { ...DEFAULT_PREFS };
  for (const key of Object.keys(DEFAULT_PREFS) as (keyof Prefs)[]) {
    const def = DEFAULT_PREFS[key];
    let v = r[key];
    if (v === undefined) continue;
    if (typeof def === "number") v = Number(v);
    if (typeof def === "number" && !Number.isFinite(v as number)) continue;
    if (typeof def !== typeof v) continue;
    (out as unknown as Record<string, unknown>)[key] = v;
  }
  out.size = Math.min(SUB_SIZE.max, Math.max(SUB_SIZE.min, out.size));
  out.bgo = Math.min(1, Math.max(0, out.bgo));
  out.bgVol = Math.min(0.5, Math.max(0, out.bgVol));
  if (![480, 720, 1080].includes(out.quality)) out.quality = 720;
  if (![0.75, 1, 1.25, 1.5].includes(out.speed)) out.speed = 1;
  if (!["ar", "bi", "src"].includes(out.dlMode)) out.dlMode = "ar";
  if (!["srt", "vtt", "txt"].includes(out.dlFmt)) out.dlFmt = "srt";
  if (!["system", "light", "dark"].includes(out.theme)) out.theme = "system";
  if (!["ar", "en"].includes(out.uiLang)) out.uiLang = "ar";
  if (out.position !== "top") out.position = "bottom";
  if (!["both", "tr", "src"].includes(out.tView)) out.tView = "both";
  if (out.tDensity !== "compact") out.tDensity = "cozy";
  out.tSize = Math.min(T_SIZE.max, Math.max(T_SIZE.min, Math.round(out.tSize)));
  if (!FONTS.some((f) => f.id === out.font)) out.font = DEFAULT_FONT;
  return out;
}

let prefs: Prefs | null = null;

export function usePrefs(): Prefs {
  if (!prefs) {
    prefs = reactive(sanitizePrefs(load("prefs", {}, "opts")));
    watch(prefs, (p) => save("prefs", p), { deep: true });
  }
  return prefs;
}
