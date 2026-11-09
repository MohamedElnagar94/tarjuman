import { createApp } from "vue";
import "@fontsource-variable/readex-pro/wght.css";
import "@fontsource-variable/reem-kufi/wght.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-500.css";
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
