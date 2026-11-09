// Renders assets/brand/icon.svg to every PNG size the app, the extension and the store need.
import { Resvg } from "@resvg/resvg-js";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const svg = fs.readFileSync(path.join(root, "assets/brand/icon.svg"), "utf8");
const render = (size) => new Resvg(svg, { fitTo: { mode: "width", value: size } }).render().asPng();

const targets = {
  "assets/brand": [16, 32, 48, 64, 128, 256, 512, 1024],
  "extension/public/icons": [16, 32, 48, 128],
  "frontend/public": [32, 180, 192, 512],
};
for (const [dir, sizes] of Object.entries(targets)) {
  fs.mkdirSync(path.join(root, dir), { recursive: true });
  for (const s of sizes) fs.writeFileSync(path.join(root, dir, `icon-${s}.png`), render(s));
}
fs.copyFileSync(path.join(root, "assets/brand/icon.svg"), path.join(root, "frontend/public/favicon.svg"));
fs.copyFileSync(path.join(root, "assets/brand/icon.svg"), path.join(root, "extension/public/icons/icon.svg"));
console.log("icons rendered");
