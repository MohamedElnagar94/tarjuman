/* The languages Tarjuman translates and dubs into: every language Microsoft's neural voices speak (the
   backend's core/langs.py has the same list). Names come from the browser in the interface's language. */

export const TARGET_LANGS = [
  "ar", "en", "fr", "es", "de", "tr", "af", "am", "az", "bg", "bn", "bs", "ca", "cs", "cy", "da", "el", "et", "fa",
  "fi", "fil", "ga", "gl", "gu", "he", "hi", "hr", "hu", "id", "is", "it", "ja", "jv", "ka", "kk", "km", "kn", "ko",
  "lo", "lt", "lv", "mk", "ml", "mn", "mr", "ms", "mt", "my", "nb", "ne", "nl", "pl", "ps", "pt", "ro", "ru", "si",
  "sk", "sl", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "th", "uk", "ur", "uz", "vi", "zh", "zu",
] as const;

/** The six the app started with, offered first; the rest follow in alphabetical order of their names. */
const FIRST = ["ar", "en", "fr", "es", "de", "tr"];

const RTL = new Set(["ar", "fa", "he", "ps", "ur", "yi"]);
export const isRtl = (code: string | undefined): boolean => RTL.has(String(code || "").split("-")[0]);

const names = new Map<string, Intl.DisplayNames | null>();

/** A language's name in the interface's language ("اليابانية" / "Japanese"), from the browser. */
export function langName(code: string, uiLang: string): string {
  if (!names.has(uiLang)) {
    try {
      names.set(uiLang, new Intl.DisplayNames([uiLang], { type: "language" }));
    } catch {
      names.set(uiLang, null);
    }
  }
  try {
    return names.get(uiLang)?.of(code) || code;
  } catch {
    return code;
  }
}

/** The languages for a menu: the first six, then the rest sorted by name in the interface's language. */
export function langOptions(uiLang: string): { value: string; label: string }[] {
  const rest = TARGET_LANGS.filter((c) => !FIRST.includes(c))
    .map((c) => ({ value: c as string, label: langName(c, uiLang) }))
    .sort((a, b) => a.label.localeCompare(b.label, uiLang));
  return [...FIRST.map((c) => ({ value: c, label: langName(c, uiLang) })), ...rest];
}
