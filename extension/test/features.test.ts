import { describe, it, expect } from "vitest";
import { shortcutFor, isTypingTarget, SHORTCUT_KEYS, SHORTCUT_ORDER, withKeys, type KeyLike } from "../src/shared/shortcuts";
import { captionTime, cleanOffset, formatOffset, nudgeOffset, offsetKey, rememberOffset, videoTimeFor } from "../src/shared/timing";
import { clock, highlight, lineProgress, pieces, speakers, startsTurn, tokenize } from "../src/shared/cueText";
import { channelFromHref, channelFromInput, hasChannel, isAutoStartPage, mergeAuto, setChannel, shouldAutoStart } from "../src/shared/autostart";
import { cueIndexAt, lastStartedIndex, stepLine } from "../src/shared/cues";
import { mergeSettings } from "../src/shared/settings";

const key = (code: string, mods: Partial<KeyLike> = {}): KeyLike => ({ code, altKey: false, shiftKey: false, ctrlKey: false, metaKey: false, ...mods });

describe("page shortcuts", () => {
  it("maps Alt + arrows like the web app: right is next, left is previous", () => {
    expect(shortcutFor(key("ArrowRight", { altKey: true }))).toBe("next");
    expect(shortcutFor(key("ArrowLeft", { altKey: true }))).toBe("prev");
    expect(shortcutFor(key("ArrowDown", { altKey: true }))).toBe("repeat");
  });

  it("has one-key bracket alternatives, and Alt + brackets for the timing", () => {
    expect(shortcutFor(key("BracketLeft"))).toBe("prev");
    expect(shortcutFor(key("BracketRight"))).toBe("next");
    expect(shortcutFor(key("Backslash"))).toBe("repeat");
    expect(shortcutFor(key("IntlBackslash"))).toBe("repeat");
    expect(shortcutFor(key("BracketLeft", { altKey: true }))).toBe("earlier");
    expect(shortcutFor(key("BracketRight", { altKey: true }))).toBe("later");
    expect(shortcutFor(key("Backslash", { altKey: true }))).toBe("resetTiming");
    expect(shortcutFor(key("KeyS", { altKey: true }))).toBe("subs");
    expect(shortcutFor(key("KeyV", { altKey: true }))).toBe("dub");
    expect(shortcutFor(key("KeyT", { altKey: true }))).toBe("transcript");
  });

  it("leaves YouTube's own keys and modified keys alone", () => {
    for (const code of ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "KeyK", "KeyJ", "KeyL", "KeyC", "KeyF", "KeyM", "KeyT", "KeyI", "Comma", "Period", "Minus", "Equal", "Slash", "Digit0", "Space", "KeyS", "KeyV"]) {
      expect(shortcutFor(key(code)), code).toBeNull();
    }
    expect(shortcutFor(key("KeyN", { shiftKey: true }))).toBeNull();
    expect(shortcutFor(key("BracketLeft", { ctrlKey: true }))).toBeNull();
    expect(shortcutFor(key("BracketLeft", { metaKey: true }))).toBeNull();
    expect(shortcutFor(key("BracketLeft", { shiftKey: true }))).toBeNull();
    expect(shortcutFor(key("ArrowUp", { altKey: true }))).toBeNull();
    expect(shortcutFor(key("BracketLeft", { isComposing: true }))).toBeNull();
  });

  it("matches the physical key, whatever the layout types there", () => {
    // On an Arabic layout "[" types "ج": the code is still BracketLeft.
    expect(shortcutFor({ ...key("BracketLeft"), key: "ج" } as KeyLike)).toBe("prev");
  });

  it("lists every action with its keys", () => {
    expect(new Set(SHORTCUT_ORDER)).toEqual(new Set(Object.keys(SHORTCUT_KEYS)));
    expect(withKeys("Next line", "next")).toBe("Next line (Alt+→ / ])");
  });

  it("knows when the user is typing", () => {
    const el = (tagName: string, extra: Record<string, unknown> = {}) => ({ tagName, getAttribute: (n: string) => (extra.attrs as any)?.[n] ?? null, ...extra });
    expect(isTypingTarget(el("INPUT", { type: "text" }))).toBe(true);
    expect(isTypingTarget(el("INPUT", { type: "search" }))).toBe(true);
    expect(isTypingTarget(el("INPUT", { type: "" }))).toBe(true);
    expect(isTypingTarget(el("INPUT", { type: "checkbox" }))).toBe(false);
    expect(isTypingTarget(el("INPUT", { type: "range" }))).toBe(false);
    expect(isTypingTarget(el("TEXTAREA"))).toBe(true);
    expect(isTypingTarget(el("SELECT"))).toBe(true);
    // YouTube's comment box
    expect(isTypingTarget(el("DIV", { isContentEditable: true }))).toBe(true);
    expect(isTypingTarget(el("DIV", { attrs: { role: "textbox" } }))).toBe(true);
    expect(isTypingTarget(el("VIDEO"))).toBe(false);
    expect(isTypingTarget(el("BUTTON"))).toBe(false);
    expect(isTypingTarget(null)).toBe(false);
  });
});

describe("lines", () => {
  const cues = [
    { start: 1, end: 3, src: "a" },
    { start: 4, end: 6, src: "b" },
    { start: 6, end: 9, src: "c" },
  ];

  it("finds the line just said, in gaps too", () => {
    expect(lastStartedIndex(cues, 0)).toBe(-1);
    expect(lastStartedIndex(cues, 3.5)).toBe(0);
    expect(lastStartedIndex(cues, 6)).toBe(2);
    expect(lastStartedIndex(cues, 100)).toBe(2);
  });

  it("steps to the previous, same and next line, within bounds", () => {
    expect(stepLine(cues, 5, 1)).toBe(2);
    expect(stepLine(cues, 5, -1)).toBe(0);
    expect(stepLine(cues, 5, 0)).toBe(1);
    expect(stepLine(cues, 3.5, 0)).toBe(0); // in a gap: the line just said
    expect(stepLine(cues, 8, 1)).toBe(2);
    expect(stepLine(cues, 1.5, -1)).toBe(0);
    expect(stepLine(cues, 0, 1)).toBe(0);
    expect(stepLine(cues, 0, -1)).toBe(0);
    expect(stepLine([], 5, 1)).toBe(-1);
  });
});

describe("subtitle timing", () => {
  it("shifts the caption clock and maps lines back to video time", () => {
    // Shown 0.5 s later: at video 10.5 s we show the caption of 10 s.
    expect(captionTime(10.5, 0.5)).toBe(10);
    expect(captionTime(10, -0.25)).toBe(10.25);
    expect(captionTime(0.1, 0.5)).toBe(0);
    expect(videoTimeFor(10, 0.5)).toBe(10.5);
    expect(videoTimeFor(0.1, -0.5)).toBe(0);
    const cues = [{ start: 10, end: 12, src: "x" }];
    expect(cueIndexAt(cues, captionTime(10.2, 0.5))).toBe(-1);
    expect(cueIndexAt(cues, captionTime(10.6, 0.5))).toBe(0);
  });

  it("nudges in steps without float noise, within limits", () => {
    let o = 0;
    for (let i = 0; i < 3; i++) o = nudgeOffset(o, 0.25);
    expect(o).toBe(0.75);
    o = nudgeOffset(o, -0.5);
    expect(o).toBe(0.25);
    expect(nudgeOffset(0.25, -0.25)).toBe(0);
    expect(Object.is(nudgeOffset(-0.25, 0.25), -0)).toBe(false);
    expect(nudgeOffset(19.9, 0.5)).toBe(20);
    expect(nudgeOffset(-19.9, -0.5)).toBe(-20);
    expect(cleanOffset("abc")).toBe(0);
    expect(cleanOffset(Infinity)).toBe(0);
    expect(cleanOffset("0.333")).toBe(0.33);
  });

  it("formats with a sign", () => {
    expect(formatOffset(0)).toBe("0.00");
    expect(formatOffset(0.5)).toBe("+0.50");
    expect(formatOffset(-0.25)).toBe("−0.25");
  });

  it("keys by video, and keeps a bounded memory", () => {
    expect(offsetKey("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30")).toBe("yt:dQw4w9WgXcQ");
    expect(offsetKey("https://youtu.be/dQw4w9WgXcQ")).toBe("yt:dQw4w9WgXcQ");
    expect(offsetKey("https://www.coursera.org/learn/x/lecture/y?z=1#t")).toBe("https://www.coursera.org/learn/x/lecture/y");
    let m: Record<string, number> = {};
    m = rememberOffset(m, "a", 0.5, 2);
    m = rememberOffset(m, "b", -0.25, 2);
    m = rememberOffset(m, "c", 1, 2);
    expect(m).toEqual({ b: -0.25, c: 1 });
    m = rememberOffset(m, "b", 0, 2); // back to zero: forgotten
    expect(m).toEqual({ c: 1 });
  });
});

describe("caption text (as in the web app)", () => {
  it("finds speaker turns and alternates speakers", () => {
    expect(startsTurn(">> Hello")).toBe(true);
    expect(startsTurn("- Yes.")).toBe(true);
    expect(startsTurn("well-known")).toBe(false);
    expect(speakers(["intro", ">> A", "more", ">> B", ">> A again"])).toEqual([0, 0, 0, 1, 0]);
    expect(speakers(["no", "turns"])).toEqual([0, 0]);
  });

  it("turns sound tags into marks and keeps ordinary parentheses", () => {
    expect(pieces(">> [Music] Hello")).toEqual([
      { kind: "tag", sound: "music", label: "Music" },
      { kind: "text", text: " Hello" },
    ]);
    expect(pieces("Thanks (applause) all")).toEqual([
      { kind: "text", text: "Thanks " },
      { kind: "tag", sound: "applause", label: "applause" },
      { kind: "text", text: " all" },
    ]);
    expect(pieces("♪ la la ♪")[0]).toEqual({ kind: "tag", sound: "music", label: "♪" });
    expect(pieces("[تصفيق]")).toEqual([{ kind: "tag", sound: "applause", label: "تصفيق" }]);
    expect(pieces("[inaudible]")).toEqual([{ kind: "tag", sound: "other", label: "inaudible" }]);
    expect(pieces("a function (like this)")).toEqual([{ kind: "text", text: "a function (like this)" }]);
    expect(pieces("[Laughter]")[0]).toMatchObject({ sound: "laughter" });
  });

  it("cuts a line into clickable words, in any script", () => {
    const tk = tokenize("Hello, world! don't stop rock-'n'-roll.");
    expect(tk.filter((x) => x.word).map((x) => (x as { lookup: string }).lookup)).toEqual(["Hello", "world", "don't", "stop", "rock-'n'-roll"]);
    expect(tk.map((x) => x.text).join("")).toBe("Hello, world! don't stop rock-'n'-roll.");
    expect(tokenize("¿Qué tal, señor?").filter((x) => x.word).map((x) => x.text)).toEqual(["Qué", "tal", "señor"]);
    expect(tokenize("42 ...").every((x) => !x.word)).toBe(true);
    expect(tokenize("")).toEqual([]);
  });

  it("highlights matches, fills the line and prints times", () => {
    expect(highlight("Hello hello", "hello")).toEqual([
      { text: "Hello", hit: true },
      { text: " ", hit: false },
      { text: "hello", hit: true },
    ]);
    expect(highlight("x", " ")).toEqual([{ text: "x", hit: false }]);
    expect(lineProgress(10, 12, 11)).toBe(0.5);
    expect(lineProgress(10, 12, 9)).toBe(0);
    expect(lineProgress(10, 12, 13)).toBe(1);
    expect(lineProgress(10, 10, 10.15)).toBeCloseTo(0.5); // very short lines count as 0.3 s
    expect(clock(65)).toBe("1:05");
    expect(clock(3723)).toBe("1:02:03");
    expect(clock(-3)).toBe("0:00");
  });
});

describe("auto-start", () => {
  const W = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";

  it("reads channel links", () => {
    expect(channelFromHref("/@freeCodeCamp")).toBe("@freecodecamp");
    expect(channelFromHref("https://www.youtube.com/@Veritasium/videos")).toBe("@veritasium");
    expect(channelFromHref("/@%D9%82%D9%86%D8%A7%D8%A9")).toBe("@قناة");
    expect(channelFromHref("/channel/UC8butISFwT-Wl7EV0hUK0BQ")).toBe("channel/UC8butISFwT-Wl7EV0hUK0BQ");
    expect(channelFromHref("/watch?v=x")).toBeNull();
    expect(channelFromHref("")).toBeNull();
    expect(channelFromInput("@FreeCodeCamp")).toBe("@freecodecamp");
    expect(channelFromInput("youtube.com/@freecodecamp")).toBe("@freecodecamp");
    expect(channelFromInput("UC8butISFwT-Wl7EV0hUK0BQ")).toBe("channel/UC8butISFwT-Wl7EV0hUK0BQ");
    expect(channelFromInput("hello world")).toBeNull();
  });

  it("is off by default and cleans what it reads", () => {
    expect(mergeAuto(null)).toEqual({ mode: "off", channels: [] });
    const r = mergeAuto({ mode: "evil", channels: [{ id: "@A", name: "A" }, { id: "@a", name: "dup" }, { id: "nope" }, 5, null] });
    expect(r).toEqual({ mode: "off", channels: [{ id: "@a", name: "A" }] });
  });

  it("starts on watch pages only, as chosen", () => {
    const off = mergeAuto(null);
    const always = mergeAuto({ mode: "always" });
    const some = mergeAuto({ mode: "channels", channels: [{ id: "@veritasium", name: "Veritasium" }] });
    expect(shouldAutoStart(off, W, "@veritasium")).toBe(false);
    expect(shouldAutoStart(always, W, null)).toBe(true);
    expect(shouldAutoStart(some, W, "@veritasium")).toBe(true);
    expect(shouldAutoStart(some, W, "@other")).toBe(false);
    expect(shouldAutoStart(some, W, null)).toBe(false);
    expect(shouldAutoStart(always, "https://www.youtube.com/shorts/dQw4w9WgXcQ", null)).toBe(false);
    expect(shouldAutoStart(always, "https://www.youtube.com/", null)).toBe(false);
    expect(shouldAutoStart(always, "https://vimeo.com/123", null)).toBe(false);
    expect(isAutoStartPage("https://m.youtube.com/watch?v=dQw4w9WgXcQ")).toBe(true);
  });

  it("adds and removes a channel from the popup's switch", () => {
    let r = mergeAuto(null);
    r = setChannel(r, { id: "@Veritasium", name: "Veritasium" }, true);
    expect(r.mode).toBe("channels"); // adding one turns the list on
    expect(hasChannel(r, "@veritasium")).toBe(true);
    r = setChannel(r, { id: "@veritasium", name: "Veritasium" }, true);
    expect(r.channels).toHaveLength(1);
    r = setChannel(r, { id: "@veritasium", name: "" }, false);
    expect(r.channels).toHaveLength(0);
    expect(setChannel(mergeAuto({ mode: "always" }), { id: "@x", name: "X" }, true).mode).toBe("always");
  });
});

describe("new settings", () => {
  it("has page keys on and the transcript off by default", () => {
    expect(mergeSettings(null).keys).toBe(true);
    expect(mergeSettings(null).transcript).toBe(false);
    expect(mergeSettings(null, { keys: false, transcript: 1 as any }).keys).toBe(false);
    expect(mergeSettings(null, { transcript: 1 as any }).transcript).toBe(true);
  });
});
