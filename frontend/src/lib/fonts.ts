// Subtitle fonts. All are bundled with the app (no font is fetched from the internet), and a font's
// files are loaded only when it is chosen. The family names match the @font-face rules in fonts.css.
// The extension keeps the same ids, so one choice reads the same in both (extension/src/shared/fonts.ts).

export type FontId = "readex" | "cairo" | "naskh" | "amiri" | "tajawal" | "kufi" | "system";

export interface SubtitleFont {
  id: FontId;
  /** CSS font-family stack. */
  family: string;
  /** The weight the translated line uses with this font. */
  weight: number;
}

const FALLBACK = '"Segoe UI", Tahoma, system-ui, sans-serif';

export const FONTS: readonly SubtitleFont[] = [
  { id: "readex", family: `"Readex Pro Variable", "Readex Pro", ${FALLBACK}`, weight: 600 },
  { id: "cairo", family: `"Cairo Variable", "Cairo", ${FALLBACK}`, weight: 600 },
  { id: "naskh", family: `"Noto Naskh Arabic", ${FALLBACK}`, weight: 600 },
  { id: "amiri", family: `"Amiri", ${FALLBACK}`, weight: 700 },
  { id: "tajawal", family: `"Tajawal", ${FALLBACK}`, weight: 700 },
  { id: "kufi", family: `"Noto Kufi Arabic Variable", "Noto Kufi Arabic", ${FALLBACK}`, weight: 600 },
  { id: "system", family: FALLBACK, weight: 600 },
];

export const DEFAULT_FONT: FontId = "readex";

export function subtitleFont(id: string | undefined): SubtitleFont {
  return FONTS.find((f) => f.id === id) || FONTS[0]!;
}
