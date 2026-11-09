// Zips dist/ (without source maps) into tarjuman-extension-<version>.zip for the Chrome Web Store.
import { zipSync } from "fflate";
import { readdirSync, readFileSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join, relative, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
if (!existsSync(join(dist, "manifest.json"))) {
  console.error("dist/manifest.json is missing: run `npm run build` first.");
  process.exit(1);
}
const { version } = JSON.parse(readFileSync(join(dist, "manifest.json"), "utf8"));

const files = {};
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (!name.endsWith(".map")) files[relative(dist, p).split("\\").join("/")] = readFileSync(p);
  }
};
walk(dist);

const out = join(root, `tarjuman-extension-${version}.zip`);
writeFileSync(out, zipSync(files, { level: 9 }));
console.log(`${relative(root, out)}  ${Object.keys(files).length} files, ${(statSync(out).size / 1024).toFixed(0)} KB`);
