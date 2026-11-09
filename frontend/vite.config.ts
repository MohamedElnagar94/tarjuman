import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import VueI18nPlugin from "@intlify/unplugin-vue-i18n/vite";

// The local backend. Override with TARJUMAN_API=http://127.0.0.1:4400 to test against another server.
const API = process.env.TARJUMAN_API || "http://127.0.0.1:4318";
const sharedEngine = fileURLToPath(new URL("../shared/dub-engine/src/index.js", import.meta.url));

export default defineConfig({
  base: "/",
  plugins: [
    vue(),
    // Precompile the locale JSON so the runtime-only vue-i18n build is enough (no message compiler, no eval).
    VueI18nPlugin({
      include: [fileURLToPath(new URL("./src/locales/**", import.meta.url))],
      runtimeOnly: true,
      compositionOnly: true,
      fullInstall: false,
      strictMessage: false,
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@tarjuman/dub-engine": sharedEngine,
    },
  },
  server: {
    port: 5173,
    host: true,
    fs: { allow: [fileURLToPath(new URL("..", import.meta.url))] },
    proxy: {
      "/api": { target: API, changeOrigin: false },
      "/dub-engine.js": { target: API, changeOrigin: false },
    },
  },
  preview: {
    proxy: {
      "/api": { target: API, changeOrigin: false },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
    assetsInlineLimit: 0,
  },
});
