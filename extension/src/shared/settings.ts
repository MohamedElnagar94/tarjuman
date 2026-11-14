import { DEFAULT_FONT, isFontId, type FontId } from "./fonts";

export type Position = "bottom" | "top";

export interface Settings {
  /** Target language. */
  lang: string;
  dub: boolean;
  /** "" = the server's default voice for the language (the first one listed). */
  voice: string;
  /** Hold the video briefly instead of letting the dub fall behind. */
  dubWait: boolean;
  /** Original video volume while dubbing, 0..1. */
  duck: number;
  /** Show the source line above the translation. */
  bilingual: boolean;
  /** Subtitle size in px for a 900px-wide player; the overlay scales it with the player. */
  size: number;
  position: Position;
  /** Opacity of the plate behind subtitles, 0..1. */
  bgOpacity: number;
  /** Subtitle font (shared/fonts.ts). */
  font: FontId;
  /** Keyboard shortcuts on the page while translating (shared/shortcuts.ts). */
  keys: boolean;
  /** The transcript panel beside the video (or floating, outside YouTube). */
  transcript: boolean;
}

export const DEFAULT_SETTINGS: Readonly<Settings> = Object.freeze({
  lang: "ar",
  dub: false,
  voice: "",
  dubWait: true,
  duck: 0.15,
  bilingual: false,
  size: 26,
  position: "bottom",
  bgOpacity: 0.78,
  font: DEFAULT_FONT,
  keys: true,
  transcript: false,
});

export const SIZE_MIN = 14;
export const SIZE_MAX = 48;

/** Every language the app translates and dubs into (the app's core/langs.py has the same list). */
export const TARGET_CODES = [
  "ar", "en", "fr", "es", "de", "tr", "af", "am", "az", "bg", "bn", "bs", "ca", "cs", "cy", "da", "el", "et", "fa",
  "fi", "fil", "ga", "gl", "gu", "he", "hi", "hr", "hu", "id", "is", "it", "ja", "jv", "ka", "kk", "km", "kn", "ko",
  "lo", "lt", "lv", "mk", "ml", "mn", "mr", "ms", "mt", "my", "nb", "ne", "nl", "pl", "ps", "pt", "ro", "ru", "si",
  "sk", "sl", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "th", "uk", "ur", "uz", "vi", "zh", "zu",
];

/** The languages for a menu, named in the interface's language: the first six, then the rest by name. */
export function targetLangs(ui: string): { code: string; name: string }[] {
  let dn: Intl.DisplayNames | null = null;
  try {
    dn = new Intl.DisplayNames([ui], { type: "language" });
  } catch {}
  const name = (c: string) => {
    try {
      return dn?.of(c) || c;
    } catch {
      return c;
    }
  };
  const all = TARGET_CODES.map((code) => ({ code, name: name(code) }));
  return [...all.slice(0, 6), ...all.slice(6).sort((a, b) => a.name.localeCompare(b.name, ui))];
}

const RTL_LANGS = new Set(["ar", "fa", "he", "ur", "ps", "ku", "yi"]);
export const langDir = (code: string): "rtl" | "ltr" => (RTL_LANGS.has(String(code).split("-")[0]) ? "rtl" : "ltr");

const clamp = (v: unknown, lo: number, hi: number, dflt: number) => {
  if (v === null || v === "" || typeof v === "boolean") return dflt;
  const n = Number(v);
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : dflt;
};

/**
 * Merges a partial, untrusted patch (storage, messages) into settings.
 * Unknown keys are dropped and every value is coerced to a valid one.
 */
export function mergeSettings(base?: Partial<Settings> | null, patch?: Partial<Settings> | null): Settings {
  const b = { ...DEFAULT_SETTINGS, ...(base || {}) } as Record<string, unknown>;
  const p = (patch || {}) as Record<string, unknown>;
  const v = (k: keyof Settings) => (p[k] !== undefined ? p[k] : b[k]);
  const lang = String(v("lang") || DEFAULT_SETTINGS.lang).trim().toLowerCase().split(/[-_]/)[0];
  return {
    lang: /^[a-z]{2,3}$/.test(lang) ? lang : DEFAULT_SETTINGS.lang,
    dub: !!v("dub"),
    voice: typeof v("voice") === "string" ? (v("voice") as string) : "",
    dubWait: v("dubWait") !== false,
    duck: clamp(v("duck"), 0, 1, DEFAULT_SETTINGS.duck),
    bilingual: !!v("bilingual"),
    size: Math.round(clamp(v("size"), SIZE_MIN, SIZE_MAX, DEFAULT_SETTINGS.size)),
    position: v("position") === "top" ? "top" : "bottom",
    bgOpacity: clamp(v("bgOpacity"), 0, 1, DEFAULT_SETTINGS.bgOpacity),
    font: isFontId(v("font")) ? (v("font") as FontId) : DEFAULT_FONT,
    keys: v("keys") !== false,
    transcript: !!v("transcript"),
  };
}

/** Keys whose values differ between two settings objects. */
export function changedKeys(prev: Settings, next: Settings): (keyof Settings)[] {
  return (Object.keys(next) as (keyof Settings)[]).filter((k) => prev[k] !== next[k]);
}
