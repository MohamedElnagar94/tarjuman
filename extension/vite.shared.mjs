// Shared by vite.config.ts (the pages) and scripts/build.mjs (service worker and content script).
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";

export const root = fileURLToPath(new URL(".", import.meta.url));
export const version = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")).version;

export const alias = {
  "@": fileURLToPath(new URL("./src", import.meta.url)),
  // The shared live dub engine is bundled in, never loaded at runtime.
  "@tarjuman/dub-engine": fileURLToPath(new URL("../shared/dub-engine/src/index.js", import.meta.url)),
};
