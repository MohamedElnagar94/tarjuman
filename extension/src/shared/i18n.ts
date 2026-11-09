/** All UI strings come from _locales; the UI follows the browser language. */
export function t(key: string, subs?: string | string[]): string {
  try {
    return chrome.i18n.getMessage(key, subs as string[]) || key;
  } catch {
    return key;
  }
}

export function uiDir(): "rtl" | "ltr" {
  try {
    return chrome.i18n.getMessage("@@bidi_dir") === "rtl" ? "rtl" : "ltr";
  } catch {
    return "ltr";
  }
}

export function uiLang(): string {
  try {
    return chrome.i18n.getMessage("@@ui_locale").split(/[-_]/)[0] || "en";
  } catch {
    return "en";
  }
}

/** Sets lang/dir on <html> and the translated title. */
export function localizeDocument(titleKey?: string) {
  document.documentElement.lang = uiLang();
  document.documentElement.dir = uiDir();
  if (titleKey) document.title = t(titleKey);
}
