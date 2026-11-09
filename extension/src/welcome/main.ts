import { createApp } from "vue";
import "@/ui/fonts";
import { localizeDocument } from "@/shared/i18n";
import App from "./App.vue";

localizeDocument("welcomeDocTitle");
createApp(App).mount("#app");
