/**
 * Subtitle fonts. The files ship with the extension (scripts/build.mjs copies them into fonts/) and
 * are declared on the page under names no site uses; a font downloads only when it is chosen.
 * The ids match the web app's subtitle fonts, except the default (IBM Plex Sans Arabic here).
 */

export type FontId = "plex" | "cairo" | "naskh" | "amiri" | "tajawal" | "kufi" | "system";

export const FONT_IDS: readonly FontId[] = ["plex", "cairo", "naskh", "amiri", "tajawal", "kufi", "system"];
export const DEFAULT_FONT: FontId = "plex";

export const RANGES = {
  arabic:
    "U+0600-06FF,U+0750-077F,U+0870-088E,U+0890-0891,U+0897-08E1,U+08E3-08FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE70-FE74,U+FE76-FEFC",
  "latin-ext":
    "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
  latin:
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
};

const SYSTEM = '"Segoe UI", "Noto Sans Arabic", Tahoma, Arial, sans-serif';

export const FONT_STACK: Record<FontId, string> = {
  plex: `"Tarjuman Sans", "IBM Plex Sans Arabic", ${SYSTEM}`,
  cairo: `"Tarjuman Cairo", ${SYSTEM}`,
  naskh: `"Tarjuman Naskh", ${SYSTEM}`,
  amiri: `"Tarjuman Amiri", ${SYSTEM}`,
  tajawal: `"Tarjuman Tajawal", ${SYSTEM}`,
  kufi: `"Tarjuman Kufi", ${SYSTEM}`,
  system: SYSTEM,
};

/** The extra fonts' files (Arabic and Latin). Keep in step with scripts/build.mjs. One file serves every
 *  weight (declared 100–900), so the browser never fakes bold from it. */
export const EXTRA_FONTS: { family: string; files: { arabic: string; latin: string } }[] = [
  { family: "Tarjuman Cairo", files: { arabic: "cairo-arabic-wght-normal.woff2", latin: "cairo-latin-wght-normal.woff2" } },
  { family: "Tarjuman Naskh", files: { arabic: "noto-naskh-arabic-arabic-600-normal.woff2", latin: "noto-naskh-arabic-latin-600-normal.woff2" } },
  { family: "Tarjuman Amiri", files: { arabic: "amiri-arabic-700-normal.woff2", latin: "amiri-latin-700-normal.woff2" } },
  { family: "Tarjuman Tajawal", files: { arabic: "tajawal-arabic-700-normal.woff2", latin: "tajawal-latin-700-normal.woff2" } },
  { family: "Tarjuman Kufi", files: { arabic: "noto-kufi-arabic-arabic-wght-normal.woff2", latin: "noto-kufi-arabic-latin-wght-normal.woff2" } },
];

export function isFontId(v: unknown): v is FontId {
  return typeof v === "string" && (FONT_IDS as readonly string[]).includes(v);
}

/** @font-face rules for the extra fonts; ``url`` turns a file name into its address. */
export function extraFontFaces(url: (file: string) => string): string {
  const out: string[] = [];
  for (const f of EXTRA_FONTS) {
    for (const subset of ["arabic", "latin"] as const) {
      out.push(
        `@font-face{font-family:"${f.family}";font-style:normal;font-weight:100 900;font-display:swap;` +
          `src:url("${url(f.files[subset])}") format("woff2");unicode-range:${RANGES[subset]};}`,
      );
    }
  }
  return out.join("\n");
}
