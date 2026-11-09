// Renders the store promo images: scripts/promo/*.svg templates → store/promo/*.svg (self-contained) and *.png, with resvg.
// resvg reads TTF/OTF only, and @fontsource ships WOFF, so each WOFF 1.0 file is
// unpacked to a plain sfnt in memory (WOFF 1.0 is just zlib-compressed tables).
import { Resvg } from "@resvg/resvg-js";
import { readFileSync, writeFileSync, mkdirSync, mkdtempSync, rmSync, readdirSync } from "node:fs";
import { inflateSync } from "node:zlib";
import { join, resolve, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const promo = join(root, "store/promo");
const templates = join(root, "scripts/promo");
const require = createRequire(import.meta.url);

/** A minimal name table (Windows, English) so each subset file gets its own family name. */
function nameTable(family) {
  const recs = [[1, family], [2, "Regular"], [4, family], [6, family.replace(/\s+/g, "")]];
  const strings = recs.map(([, v]) => Buffer.from(v, "utf16le").swap16());
  const head = Buffer.alloc(6 + 12 * recs.length);
  head.writeUInt16BE(0, 0);
  head.writeUInt16BE(recs.length, 2);
  head.writeUInt16BE(head.length, 4);
  let off = 0;
  recs.forEach(([id], i) => {
    const r = 6 + i * 12;
    head.writeUInt16BE(3, r);
    head.writeUInt16BE(1, r + 2);
    head.writeUInt16BE(0x409, r + 4);
    head.writeUInt16BE(id, r + 6);
    head.writeUInt16BE(strings[i].length, r + 8);
    head.writeUInt16BE(off, r + 10);
    off += strings[i].length;
  });
  return Buffer.concat([head, ...strings]);
}

function woffToSfnt(woff, family) {
  if (woff.toString("ascii", 0, 4) !== "wOFF") throw new Error("not a WOFF 1.0 file");
  const flavor = woff.readUInt32BE(4);
  const numTables = woff.readUInt16BE(12);
  const tables = [];
  for (let i = 0; i < numTables; i++) {
    const o = 44 + i * 20;
    const tag = woff.toString("latin1", o, o + 4);
    const offset = woff.readUInt32BE(o + 4);
    const compLength = woff.readUInt32BE(o + 8);
    const origLength = woff.readUInt32BE(o + 12);
    const checksum = woff.readUInt32BE(o + 16);
    const raw = woff.subarray(offset, offset + compLength);
    const data = tag === "name" && family ? nameTable(family) : compLength < origLength ? inflateSync(raw) : raw;
    tables.push({ tag, checksum, data });
  }
  let pow = 1;
  let log = 0;
  while (pow * 2 <= numTables) {
    pow *= 2;
    log++;
  }
  const headerLen = 12 + 16 * numTables;
  const total = headerLen + tables.reduce((n, t) => n + Math.ceil(t.data.length / 4) * 4, 0);
  const out = Buffer.alloc(total);
  out.writeUInt32BE(flavor, 0);
  out.writeUInt16BE(numTables, 4);
  out.writeUInt16BE(pow * 16, 6);
  out.writeUInt16BE(log, 8);
  out.writeUInt16BE(numTables * 16 - pow * 16, 10);
  let off = headerLen;
  tables.forEach((t, i) => {
    const r = 12 + i * 16;
    out.write(t.tag, r, "latin1");
    out.writeUInt32BE(t.checksum, r + 4);
    out.writeUInt32BE(off, r + 8);
    out.writeUInt32BE(t.data.length, r + 12);
    t.data.copy(out, off);
    off += Math.ceil(t.data.length / 4) * 4;
  });
  return out;
}

const tmp = mkdtempSync(join(tmpdir(), "tarjuman-fonts-"));
const fontFiles = [];
// The subsets share one family name, so a font matcher would pick a subset without the
// glyphs it needs. Each subset gets a family of its own: "Plex Latin", "Kufi Arabic", …
const addFont = (pkg, file, family) => {
  const dir = dirname(require.resolve(`${pkg}/package.json`));
  const p = join(tmp, file.replace(/\.woff$/, ".ttf"));
  writeFileSync(p, woffToSfnt(readFileSync(join(dir, "files", file)), family));
  fontFiles.push(p);
};
for (const [s, S] of [["arabic", "Arabic"], ["latin", "Latin"]]) {
  addFont("@fontsource/reem-kufi", `reem-kufi-${s}-600-normal.woff`, `Kufi ${S}`);
  for (const w of [400, 500, 700]) addFont("@fontsource/ibm-plex-sans-arabic", `ibm-plex-sans-arabic-${s}-${w}-normal.woff`, `Plex ${S}`);
}

// The icon goes in as a nested SVG image, so it stays the single source of truth.
const iconData = "data:image/svg+xml;base64," + readFileSync(join(root, "public/icons/icon.svg")).toString("base64");

mkdirSync(promo, { recursive: true });
try {
  for (const name of readdirSync(templates).filter((f) => f.endsWith(".svg"))) {
    const svg = readFileSync(join(templates, name), "utf8").replaceAll("{{ICON}}", iconData);
    writeFileSync(join(promo, name), svg);
    const png = new Resvg(svg, {
      font: { fontFiles, loadSystemFonts: false, defaultFontFamily: "Plex Latin" },
      fitTo: { mode: "original" },
    })
      .render()
      .asPng();
    const out = join(promo, name.replace(/\.svg$/, ".png"));
    writeFileSync(out, png);
    console.log("rendered", out);
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
