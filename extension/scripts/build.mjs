// Builds the extension into dist/: the pages (vite.config.ts), then the service
// worker (an ES module) and the content script (IIFE: content scripts can't be
// modules), then copies the overlay font and writes manifest.json.
//   node scripts/build.mjs [--watch]
import { build } from "vite";
import { build as esbuild } from "esbuild";
import { mkdirSync, rmSync, copyFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { alias, version } from "../vite.shared.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = resolve(root, "dist");
const watch = process.argv.includes("--watch");
const require = createRequire(import.meta.url);

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

function script(entry, fileName, format) {
  return build({
    root,
    configFile: false,
    logLevel: "warn",
    resolve: { alias },
    publicDir: false,
    build: {
      outDir: dist,
      emptyOutDir: false,
      target: "chrome116",
      sourcemap: true,
      minify: true,
      watch: watch ? {} : null,
      lib: { entry: resolve(root, entry), formats: [format], name: "Tarjuman", fileName: () => fileName },
      rollupOptions: { output: { inlineDynamicImports: true } },
    },
  });
}

async function writeManifest() {
  const out = await esbuild({ entryPoints: [resolve(root, "src/manifest.ts")], write: false, format: "esm", bundle: true, platform: "node" });
  const url = "data:text/javascript;base64," + Buffer.from(out.outputFiles[0].text).toString("base64");
  const { manifest } = await import(url);
  writeFileSync(resolve(dist, "manifest.json"), JSON.stringify(manifest(version), null, 2) + "\n");
}

function copyFonts() {
  mkdirSync(resolve(dist, "fonts"), { recursive: true });
  const dir = dirname(require.resolve("@fontsource/ibm-plex-sans-arabic/package.json"));
  for (const subset of ["arabic", "latin", "latin-ext"]) {
    for (const w of [500, 700]) {
      const f = `ibm-plex-sans-arabic-${subset}-${w}-normal.woff2`;
      copyFileSync(resolve(dir, "files", f), resolve(dist, "fonts", f));
    }
  }
}

await build({ configFile: resolve(root, "vite.config.ts"), logLevel: "warn", build: { emptyOutDir: false, watch: watch ? {} : null } });
await script("src/background/index.ts", "background.js", "es");
await script("src/content/index.ts", "content.js", "iife");
copyFonts();
await writeManifest();
console.log(watch ? `Watching… dist/ (v${version})` : `Built dist/ (v${version})`);
