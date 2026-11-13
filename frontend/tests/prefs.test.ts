import { describe, expect, it } from "vitest";
import { DEFAULT_PREFS, sanitizePrefs } from "@/composables/prefs";
import { KEYMAP, SHORTCUTS, shortcutFor } from "@/composables/shortcuts";

describe("sanitizePrefs", () => {
  it("returns defaults for junk", () => {
    expect(sanitizePrefs(null)).toEqual(DEFAULT_PREFS);
    expect(sanitizePrefs("x")).toEqual(DEFAULT_PREFS);
  });
  it("accepts the prototype's stored options (string speed and quality)", () => {
    const p = sanitizePrefs({ speed: "1.25", quality: "1080", size: 30, voice: "ar-EG-SalmaNeural", liveDub: true });
    expect(p.speed).toBe(1.25);
    expect(p.quality).toBe(1080);
    expect(p.size).toBe(30);
    expect(p.voice).toBe("ar-EG-SalmaNeural");
    expect(p.liveDub).toBe(true);
  });
  it("clamps and rejects bad values", () => {
    const p = sanitizePrefs({ size: 400, bgo: -1, bgVol: 9, quality: 333, speed: 7, dlMode: "x", theme: "neon", show: "yes" });
    expect(p.size).toBe(52);
    expect(p.bgo).toBe(0);
    expect(p.bgVol).toBe(0.5);
    expect(p.quality).toBe(720);
    expect(p.speed).toBe(1);
    expect(p.dlMode).toBe("ar");
    expect(p.theme).toBe("system");
    expect(p.show).toBe(true);
  });
  it("keeps a known subtitle font and replaces an unknown one", () => {
    expect(sanitizePrefs({ font: "amiri" }).font).toBe("amiri");
    expect(sanitizePrefs({ font: "comic-sans" }).font).toBe("readex");
  });
});

describe("shortcuts", () => {
  it("maps Latin and Arabic layout keys to the same action", () => {
    const k = (key: string) => shortcutFor({ key, ctrlKey: false, metaKey: false, altKey: false });
    expect(k("k")).toBe("play");
    expect(k("K")).toBe("play");
    expect(k("ن")).toBe("play");
    expect(k("ArrowLeft")).toBe("next");
    expect(k("d")).toBe("dub");
    expect(k("ي")).toBe("dub");
    expect(k("x")).toBeNull();
    expect(shortcutFor({ key: "k", ctrlKey: true, metaKey: false, altKey: false })).toBeNull();
  });
  it("lists every mapped action", () => {
    const listed = new Set(SHORTCUTS.map((s) => s.id));
    for (const id of Object.values(KEYMAP)) expect(listed.has(id)).toBe(true);
  });
});
