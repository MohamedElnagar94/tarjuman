import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";
import { alias, root } from "./vite.shared.mjs";

// Extension pages (popup, options, welcome, offscreen). Background and content
// script are built separately by scripts/build.mjs because they must be single files.
export default defineConfig({
  root,
  base: "./",
  plugins: [vue()],
  resolve: { alias },
  publicDir: "public",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "chrome116",
    sourcemap: true,
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
    rollupOptions: {
      input: {
        popup: resolve(root, "popup.html"),
        options: resolve(root, "options.html"),
        welcome: resolve(root, "welcome.html"),
        offscreen: resolve(root, "offscreen.html"),
      },
    },
  },
  test: {
    include: ["test/**/*.test.ts"],
    environment: "node",
  },
} as any);
