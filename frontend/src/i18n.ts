import { createI18n } from "vue-i18n";
import ar from "@/locales/ar.json";
import en from "@/locales/en.json";

export type MessageSchema = typeof ar;

export const i18n = createI18n({
  legacy: false,
  locale: "ar",
  fallbackLocale: "en",
  messages: { ar, en },
  missingWarn: import.meta.env.DEV,
  fallbackWarn: false,
});

const { t, te } = i18n.global;

/** A human message for an API error code; falls back to the server's own message. */
export function errText(code: string | undefined, message?: string, withDetail = false): string {
  if (code && te("errors." + code)) {
    const base = t("errors." + code);
    return withDetail && message && message !== code ? base + " (" + message + ")" : base;
  }
  return t("errors.generic", { detail: message || code || "?" });
}
