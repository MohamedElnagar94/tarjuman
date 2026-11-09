// Packs PNG renders of the icon into assets/brand/icon.ico (Windows shortcuts and the taskbar).
import { Resvg } from "@resvg/resvg-js";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const svg = fs.readFileSync(path.join(root, "assets/brand/icon.svg"), "utf8");
const sizes = [16, 24, 32, 48, 64, 128, 256];
const pngs = sizes.map((s) => new Resvg(svg, { fitTo: { mode: "width", value: s } }).render().asPng());

const header = Buffer.alloc(6);
header.writeUInt16LE(0, 0);
header.writeUInt16LE(1, 2); // icon
header.writeUInt16LE(sizes.length, 4);
const dir = Buffer.alloc(16 * sizes.length);
let offset = 6 + dir.length;
sizes.forEach((s, i) => {
  const e = i * 16;
  dir.writeUInt8(s >= 256 ? 0 : s, e);
  dir.writeUInt8(s >= 256 ? 0 : s, e + 1);
  dir.writeUInt16LE(1, e + 4); // planes
  dir.writeUInt16LE(32, e + 6); // bits per pixel
  dir.writeUInt32LE(pngs[i].length, e + 8);
  dir.writeUInt32LE(offset, e + 12);
  offset += pngs[i].length;
});
fs.writeFileSync(path.join(root, "assets/brand/icon.ico"), Buffer.concat([header, dir, ...pngs]));
console.log("assets/brand/icon.ico");
