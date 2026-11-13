/**
 * All UI strings come from _locales. By default the UI follows the browser language; the user can pick
 * Arabic or English instead (options page), stored as ``uiLang`` in chrome.storage.local.
 * chrome.i18n can't switch language at runtime, so a chosen language's messages.json is read once
 * (``readTable``) and used before chrome.i18n. Extension pages read it themselves; content scripts
 * can't read extension files, so the background reads it for them.
 */

export type UiLang = "auto" | "ar" | "en";
export const UI_LANGS: readonly UiLang[] = ["auto", "ar", "en"];

export interface Entry {
  message: string;
  placeholders?: Record<string, { content: string }>;
}
export type Table = Record<string, Entry>;

let table: Table | null = null;
let chosen: "ar" | "en" | null = null;

function browserLang(): string {
  try {
    return chrome.i18n.getMessage("@@ui_locale").split(/[-_]/)[0] || "en";
  } catch {
    return "en";
  }
}

/** Fills $NAME$ placeholders (which point at $1, $2…) and $1, $2… with ``subs``, as chrome.i18n does. */
export function format(e: Entry, subs?: string | string[]): string {
  const list = subs == null ? [] : Array.isArray(subs) ? subs : [subs];
  const fill = (s: string) => s.replace(/\$(\d)/g, (_, n) => list[Number(n) - 1] ?? "");
  const named = e.message.replace(/\$([A-Za-z0-9_@]+)\$/g, (m, name: string) => {
    const p = e.placeholders?.[name.toLowerCase()] || e.placeholders?.[name];
    return p ? fill(p.content) : m;
  });
  return fill(named).replace(/\$\$/g, "$");
}

/** The chosen language and its messages, or nulls when the browser language applies. */
export async function readTable(): Promise<{ lang: "ar" | "en" | null; table: Table | null }> {
  try {
    const { uiLang } = await chrome.storage.local.get("uiLang");
    if ((uiLang === "ar" || uiLang === "en") && uiLang !== browserLang()) {
      const r = await fetch(chrome.runtime.getURL(`_locales/${uiLang}/messages.json`));
      return { lang: uiLang, table: (await r.json()) as Table };
    }
  } catch {
    /* the browser language stays */
  }
  return { lang: null, table: null };
}

/** Extension pages: call before mounting. */
export async function loadUiLang(): Promise<void> {
  const r = await readTable();
  useTable(r.lang, r.table);
}

export function useTable(lang: "ar" | "en" | null, t: Table | null): void {
  chosen = lang;
  table = t;
}

export function t(key: string, subs?: string | string[]): string {
  const e = table?.[key];
  if (e) return format(e, subs);
  try {
    return chrome.i18n.getMessage(key, subs as string[]) || key;
  } catch {
    return key;
  }
}

export function uiLang(): string {
  return chosen || browserLang();
}

export function uiDir(): "rtl" | "ltr" {
  if (chosen) return chosen === "ar" ? "rtl" : "ltr";
  try {
    return chrome.i18n.getMessage("@@bidi_dir") === "rtl" ? "rtl" : "ltr";
  } catch {
    return "ltr";
  }
}

/** Sets lang/dir on <html> and the translated title. */
export function localizeDocument(titleKey?: string) {
  document.documentElement.lang = uiLang();
  document.documentElement.dir = uiDir();
  if (titleKey) document.title = t(titleKey);
}
