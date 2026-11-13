import { createApp } from "vue";
import "@fontsource-variable/readex-pro/wght.css";
import "@fontsource-variable/reem-kufi/wght.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
// Subtitle fonts (Settings -> Appearance). A font's files download only when it is used.
import "@fontsource-variable/cairo/wght.css";
import "@fontsource-variable/noto-kufi-arabic/wght.css";
import "@fontsource/noto-naskh-arabic/arabic-400.css";
import "@fontsource/noto-naskh-arabic/arabic-600.css";
import "@fontsource/noto-naskh-arabic/latin-400.css";
import "@fontsource/noto-naskh-arabic/latin-600.css";
import "@fontsource/amiri/arabic-400.css";
import "@fontsource/amiri/arabic-700.css";
import "@fontsource/amiri/latin-400.css";
import "@fontsource/amiri/latin-700.css";
import "@fontsource/tajawal/arabic-400.css";
import "@fontsource/tajawal/arabic-700.css";
import "@fontsource/tajawal/latin-400.css";
import "@fontsource/tajawal/latin-700.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/panels.css";
import App from "./App.vue";
import { i18n } from "./i18n";
import { router } from "./router";
import { useAppearance } from "./composables/appearance";

// Theme and language go on <html> before the first paint.
useAppearance();

createApp(App).use(i18n).use(router).mount("#app");
