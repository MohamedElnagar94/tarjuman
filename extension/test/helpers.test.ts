import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { PORTS, parseHealth, normalizeServerUrl, candidates, findServer } from "../src/shared/server";
import { cueIndexAt, ytVideoId, isYouTube, isProtectedUrl, originPattern, cleanCueText, normalizeTrackCues, pickTrack } from "../src/shared/cues";
import { Chunker, downsampleTo16k, toPcm16B64, b64ToBytes, rms } from "../src/shared/audio";
import { mergeSettings, DEFAULT_SETTINGS, changedKeys, langDir } from "../src/shared/settings";
import { manifest } from "../src/manifest";

const json = (o: unknown) => ({ ok: true, json: async () => o });

describe("server discovery", () => {
  it("scans 4318–4327", () => {
    expect(PORTS[0]).toBe(4318);
    expect(PORTS.at(-1)).toBe(4327);
    expect(PORTS).toHaveLength(10);
  });

  it("accepts Tarjuman and the prototype, nothing else", () => {
    expect(parseHealth({ ok: true, app: "tarjuman", version: "3.0.0" })?.version).toBe("3.0.0");
    expect(parseHealth({ ok: true, app: "youtube-arabic" })).not.toBeNull();
    expect(parseHealth({ ok: true, app: "something-else" })).toBeNull();
    expect(parseHealth({ ok: false, app: "tarjuman" })).toBeNull();
    expect(parseHealth("ok")).toBeNull();
    expect(parseHealth(null)).toBeNull();
  });

  it("normalizes loopback addresses and rejects everything else", () => {
    expect(normalizeServerUrl("4320")).toBe("http://127.0.0.1:4320");
    expect(normalizeServerUrl("localhost:4318/")).toBe("http://localhost:4318");
    expect(normalizeServerUrl("http://127.0.0.1:4319/api/health")).toBe("http://127.0.0.1:4319");
    expect(normalizeServerUrl("[::1]:4318")).toBe("http://[::1]:4318");
    expect(normalizeServerUrl("192.168.1.10:4318")).toBeNull();
    expect(normalizeServerUrl("https://127.0.0.1:4318")).toBeNull();
    expect(normalizeServerUrl("evil.com")).toBeNull();
    expect(normalizeServerUrl("")).toBeNull();
  });

  it("tries the last address first and an override alone", () => {
    expect(candidates(null, "http://127.0.0.1:4321")[0]).toBe("http://127.0.0.1:4321");
    expect(candidates(null, "http://127.0.0.1:4321")).toHaveLength(10);
    expect(candidates("http://localhost:9000", "http://127.0.0.1:4321")).toEqual(["http://localhost:9000"]);
    expect(candidates(null, "http://evil:1")[0]).toBe("http://127.0.0.1:4318");
  });

  it("finds the lowest answering port", async () => {
    const seen: string[] = [];
    const fetch = async (url: string) => {
      seen.push(url);
      if (url.includes(":4320") || url.includes(":4325")) return json({ ok: true, app: "tarjuman", port: Number(url.split(":")[2].split("/")[0]) });
      if (url.includes(":4318")) return json({ ok: true, app: "other" });
      throw new Error("ECONNREFUSED");
    };
    const f = await findServer({ fetch });
    expect(f?.base).toBe("http://127.0.0.1:4320");
    expect(seen).toHaveLength(10);
  });

  it("returns early when the last address still answers", async () => {
    let calls = 0;
    const fetch = async () => {
      calls++;
      return json({ ok: true, app: "tarjuman" });
    };
    const f = await findServer({ fetch, last: "http://127.0.0.1:4322" });
    expect(f?.base).toBe("http://127.0.0.1:4322");
    expect(calls).toBe(1);
  });

  it("returns null when nothing answers", async () => {
    const f = await findServer({ fetch: async () => ({ ok: false, json: async () => ({}) }) });
    expect(f).toBeNull();
  });
});

describe("cues", () => {
  const cues = [
    { start: 0, end: 2, src: "a" },
    { start: 2.5, end: 4, src: "b" },
    { start: 4, end: 6, src: "c" },
  ];

  it("finds the cue at a time, and none in gaps", () => {
    expect(cueIndexAt(cues, 0)).toBe(0);
    expect(cueIndexAt(cues, 1.99)).toBe(0);
    expect(cueIndexAt(cues, 2.2)).toBe(-1);
    expect(cueIndexAt(cues, 3)).toBe(1);
    expect(cueIndexAt(cues, 4)).toBe(2);
    expect(cueIndexAt(cues, 6)).toBe(-1);
    expect(cueIndexAt(cues, -1)).toBe(-1);
    expect(cueIndexAt([], 1)).toBe(-1);
  });

  it("parses YouTube ids from every URL shape", () => {
    expect(ytVideoId("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1")).toBe("dQw4w9WgXcQ");
    expect(ytVideoId("https://youtu.be/dQw4w9WgXcQ")).toBe("dQw4w9WgXcQ");
    expect(ytVideoId("https://www.youtube.com/shorts/dQw4w9WgXcQ")).toBe("dQw4w9WgXcQ");
    expect(ytVideoId("https://www.youtube.com/embed/dQw4w9WgXcQ")).toBe("dQw4w9WgXcQ");
    expect(ytVideoId("https://www.youtube.com/live/dQw4w9WgXcQ")).toBe("dQw4w9WgXcQ");
    expect(ytVideoId("https://www.youtube.com/")).toBe("");
  });

  it("classifies pages", () => {
    expect(isYouTube("https://m.youtube.com/watch?v=x")).toBe(true);
    expect(isYouTube("https://notyoutube.com/")).toBe(false);
    expect(isProtectedUrl("chrome://extensions")).toBe(true);
    expect(isProtectedUrl("https://chromewebstore.google.com/detail/x")).toBe(true);
    expect(isProtectedUrl("https://www.coursera.org/learn/x")).toBe(false);
    expect(isProtectedUrl("")).toBe(true);
    expect(originPattern("https://www.coursera.org/learn/x?y=1")).toBe("https://www.coursera.org/*");
    expect(originPattern("file:///c:/x.mp4")).toBeNull();
  });

  it("cleans site VTT cues", () => {
    expect(cleanCueText("<v Speaker>Hello&nbsp;<b>there</b>\n  world</v>")).toBe("Hello there world");
    const out = normalizeTrackCues([
      { startTime: 5, endTime: 6, text: "second" },
      { startTime: 1, endTime: 2, text: "first" },
      { startTime: 3, endTime: 3, text: "zero length" },
      { startTime: 4, endTime: 5, text: "  " },
    ]);
    expect(out.map((c) => c.src)).toEqual(["first", "second"]);
  });

  it("prefers an English track, then one not in the target language", () => {
    const tr = (lang: string, index: number) => ({ index, lang, label: lang });
    expect(pickTrack([tr("ar", 0), tr("en-us", 1)], "ar")?.index).toBe(1);
    expect(pickTrack([tr("ar", 0), tr("fr", 1)], "ar")?.index).toBe(1);
    expect(pickTrack([tr("ar", 0)], "ar")?.index).toBe(0);
    expect(pickTrack([], "ar")).toBeNull();
  });
});

describe("live audio chunking", () => {
  const RATE = 16000;
  const tone = (secs: number, amp = 0.2) => Float32Array.from({ length: Math.round(secs * RATE) }, (_, i) => amp * Math.sin(i / 5));
  const silence = (secs: number) => new Float32Array(Math.round(secs * RATE));
  const feed = (c: Chunker, data: Float32Array, frame = 1024) => {
    const out: (Float32Array | null)[] = [];
    for (let i = 0; i < data.length; i += frame) {
      const r = c.push(data.subarray(i, i + frame));
      if (r !== undefined) out.push(r);
    }
    return out;
  };

  it("never cuts before the minimum length", () => {
    const c = new Chunker(RATE);
    expect(feed(c, tone(2))).toEqual([]);
  });

  it("cuts at the first pause after the minimum", () => {
    const c = new Chunker(RATE);
    const out = feed(c, Float32Array.from([...tone(3), ...silence(0.5)]));
    expect(out).toHaveLength(1);
    expect(out[0]!.length / RATE).toBeGreaterThan(3);
    expect(out[0]!.length / RATE).toBeLessThan(3.6);
  });

  it("cuts continuous speech at the maximum length", () => {
    const c = new Chunker(RATE);
    const out = feed(c, tone(13));
    expect(out).toHaveLength(2);
    for (const o of out) expect(Math.abs(o!.length / RATE - 6)).toBeLessThan(0.1);
  });

  it("drops pure silence", () => {
    const c = new Chunker(RATE);
    const out = feed(c, silence(7));
    expect(out.length).toBeGreaterThan(0);
    expect(out.every((o) => o === null)).toBe(true);
    expect(c.seconds).toBeLessThan(2.5);
  });

  it("downsamples and encodes s16le", () => {
    const d = downsampleTo16k(new Float32Array(48000).fill(0.5), 48000);
    expect(d.length).toBe(16000);
    expect(d[100]).toBeCloseTo(0.5);
    const bytes = b64ToBytes(toPcm16B64(Float32Array.from([1, -1, 0])));
    const i16 = new Int16Array(bytes.buffer);
    expect([...i16]).toEqual([32767, -32768, 0]);
    expect(rms(Float32Array.from([1, -1]))).toBe(1);
  });
});

describe("settings", () => {
  it("fills defaults", () => {
    expect(mergeSettings(null)).toEqual(DEFAULT_SETTINGS);
  });

  it("merges a patch and keeps the rest", () => {
    const s = mergeSettings({ ...DEFAULT_SETTINGS, dub: true, size: 30 }, { voice: "ar-EG-SalmaNeural" });
    expect(s.dub).toBe(true);
    expect(s.size).toBe(30);
    expect(s.voice).toBe("ar-EG-SalmaNeural");
  });

  it("coerces and clamps untrusted values, drops unknown keys", () => {
    const s = mergeSettings(null, { size: 400, duck: -2, bgOpacity: "0.5" as any, position: "left" as any, lang: "AR-eg", dubWait: 0 as any, evil: 1 } as any);
    expect(s.size).toBe(48);
    expect(s.duck).toBe(0);
    expect(s.bgOpacity).toBe(0.5);
    expect(s.position).toBe("bottom");
    expect(s.lang).toBe("ar");
    expect(s.dubWait).toBe(true); // only an explicit false turns waiting off
    expect("evil" in s).toBe(false);
    expect(mergeSettings(null, { size: "x" as any }).size).toBe(26);
    expect(mergeSettings(null, { lang: "<script>" }).lang).toBe("ar");
  });

  it("reports changed keys and text direction", () => {
    expect(changedKeys(mergeSettings(null), mergeSettings(null, { lang: "en", size: 30 }))).toEqual(["lang", "size"]);
    expect(langDir("ar")).toBe("rtl");
    expect(langDir("en")).toBe("ltr");
  });
});

describe("store readiness", () => {
  const root = join(__dirname, "..");
  const load = (l: string) => JSON.parse(readFileSync(join(root, "public/_locales", l, "messages.json"), "utf8"));
  const en = load("en");
  const ar = load("ar");

  it("has the same keys in English and Arabic", () => {
    expect(Object.keys(ar).sort()).toEqual(Object.keys(en).sort());
    for (const k of Object.keys(en)) expect(ar[k].message, k).toBeTruthy();
  });

  it("has every string the code uses", () => {
    const files: string[] = [];
    const walk = (d: string) => {
      for (const f of readdirSync(d)) {
        const p = join(d, f);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.(ts|vue)$/.test(f)) files.push(p);
      }
    };
    walk(join(root, "src"));
    const used = new Set<string>();
    for (const f of files) for (const m of readFileSync(f, "utf8").matchAll(/\bt\(\s*["']([A-Za-z0-9_]+)["']/g)) used.add(m[1]);
    const mf = JSON.stringify(manifest("0.0.0"));
    for (const m of mf.matchAll(/__MSG_(\w+)__/g)) used.add(m[1]);
    const missing = [...used].filter((k) => !en[k]);
    expect(missing).toEqual([]);
  });

  it("meets the store's length limits", () => {
    for (const l of [en, ar]) {
      expect(l.extName.message.length).toBeLessThanOrEqual(75);
      expect(l.extShortName.message.length).toBeLessThanOrEqual(12);
      expect(l.extDescription.message.length).toBeLessThanOrEqual(132);
    }
  });

  it("asks only for the permissions it needs", () => {
    const m = manifest("1.2.3") as any;
    expect(m.manifest_version).toBe(3);
    expect(m.permissions.sort()).toEqual(["activeTab", "offscreen", "scripting", "storage", "tabCapture"]);
    expect(m.host_permissions).toEqual(["http://127.0.0.1/*", "http://localhost/*"]);
    expect(m.optional_host_permissions).toEqual(["<all_urls>"]);
    expect(m.permissions).not.toContain("tabs");
    expect(m.content_scripts[0].matches).toEqual(["*://*.youtube.com/*"]);
  });
});
