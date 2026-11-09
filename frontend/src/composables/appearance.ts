import { computed, ref, watch, watchEffect } from "vue";
import { i18n } from "@/i18n";
import { usePrefs } from "./prefs";

const systemDark = ref(typeof matchMedia === "function" ? matchMedia("(prefers-color-scheme: dark)").matches : true);
if (typeof matchMedia === "function") {
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => (systemDark.value = e.matches));
}

let started = false;

/** Applies the theme and UI language to <html>, and keeps them in sync with the preferences. */
export function useAppearance() {
  const prefs = usePrefs();
  const theme = computed(() => (prefs.theme === "system" ? (systemDark.value ? "dark" : "light") : prefs.theme));

  if (!started) {
    started = true;
    watchEffect(() => {
      const root = document.documentElement;
      root.dataset.theme = theme.value;
      document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme.value === "dark" ? "#0a0e26" : "#f3f5fb");
    });
    watch(
      () => prefs.uiLang,
      (lang) => {
        i18n.global.locale.value = lang;
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
      },
      { immediate: true },
    );
  }

  return {
    theme,
    toggleTheme: () => (prefs.theme = theme.value === "dark" ? "light" : "dark"),
    toggleLang: () => (prefs.uiLang = prefs.uiLang === "ar" ? "en" : "ar"),
  };
}
