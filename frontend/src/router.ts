import { createRouter, createWebHistory } from "vue-router";
import HomeView from "./views/HomeView.vue";

export const router = createRouter({
  history: createWebHistory("/"),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/watch", name: "watch", component: () => import("./views/WatchView.vue") },
    { path: "/library", name: "library", component: () => import("./views/LibraryView.vue") },
    { path: "/words", name: "words", component: () => import("./views/WordsView.vue") },
    { path: "/settings", name: "settings", component: () => import("./views/SettingsView.vue") },
    { path: "/:rest(.*)*", name: "missing", component: () => import("./views/NotFoundView.vue") },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved;
    // Settings shows one section at a time: its hash picks the section, not a place to scroll to.
    if (to.name === "settings") return to.name === from.name ? false : { top: 0 };
    if (to.hash) return { el: to.hash, top: 80 };
    if (to.name === from.name) return false;
    return { top: 0 };
  },
});
