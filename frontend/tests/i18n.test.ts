/* Every string lives in ar.json and en.json: same keys in both, and every key the code uses exists. */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import ar from "@/locales/ar.json";
import en from "@/locales/en.json";

type Tree = { [k: string]: string | Tree };

function keys(o: Tree, prefix = ""): string[] {
  return Object.entries(o).flatMap(([k, v]) => (typeof v === "string" ? [prefix + k] : keys(v, prefix + k + ".")));
}

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : /\.(vue|ts)$/.test(f) ? [p] : [];
  });
}

const arKeys = new Set(keys(ar as Tree));
const enKeys = new Set(keys(en as Tree));

describe("locales", () => {
  it("have the same keys", () => {
    expect([...arKeys].filter((k) => !enKeys.has(k))).toEqual([]);
    expect([...enKeys].filter((k) => !arKeys.has(k))).toEqual([]);
  });

  it("contain every static key used in the code", () => {
    const src = join(__dirname, "..", "src");
    const used = new Set<string>();
    const re = /(?:\$t|\bt|\bte)\(\s*["'`]([a-zA-Z][\w.-]*)["'`]/g;
    const label = /label:\s*"((?:nav)\.[\w.]+)"/g;
    for (const f of files(src)) {
      const text = readFileSync(f, "utf8");
      for (const m of text.matchAll(re)) if (!m[1]!.endsWith(".")) used.add(m[1]!);
      for (const m of text.matchAll(label)) used.add(m[1]!);
    }
    const missing = [...used].filter((k) => !arKeys.has(k));
    expect(missing).toEqual([]);
  });

  it("have no em dashes in visible copy", () => {
    const all = JSON.stringify(ar) + JSON.stringify(en);
    expect(all.includes("—")).toBe(false);
  });

  it("cover the dynamic key families", () => {
    for (const s of ["speaking", "catching-up", "waiting", "buffering", "error", "ready"]) expect(arKeys.has("dub.state." + s)).toBe(true);
    for (const s of ["whisper", "dub", "subvideo", "batch", "fetch"]) expect(arKeys.has("library.jobs.type." + s)).toBe(true);
    for (const s of ["transcript", "watch", "export", "ask", "learn"]) expect(arKeys.has("watch.tab." + s)).toBe(true);
    for (const s of ["ai", "pronounce", "defaults", "appearance", "shortcuts"]) expect(arKeys.has("settings.s." + s)).toBe(true);
    for (const s of ["up", "partial", "down", "unknown"]) expect(arKeys.has("status.dot." + s)).toBe(true);
    for (const s of ["subs", "dub", "export", "ask", "learn"]) expect(arKeys.has(`home.can.${s}.title`)).toBe(true);
    for (const s of ["ar", "en", "fr", "es", "de", "tr"]) expect(arKeys.has("langs." + s)).toBe(true);
    for (const s of ["gemini", "groq", "openrouter", "ollama"]) expect(arKeys.has("ai.preset." + s)).toBe(true);
    for (const s of ["subs", "subvideo", "dub"]) expect(arKeys.has("library.batch." + s)).toBe(true);
  });
});
