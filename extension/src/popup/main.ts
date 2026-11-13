import { createApp } from "vue";
import "@/ui/fonts";
import { loadUiLang, localizeDocument } from "@/shared/i18n";
import App from "./App.vue";

loadUiLang().then(() => {
  localizeDocument("extShortName");
  createApp(App).mount("#app");
});
