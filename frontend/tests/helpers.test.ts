import { describe, expect, it } from "vitest";
import { activeIndex, lastStartedIndex, transcriptText, translationOrder } from "@/lib/cues";
import { classifyLink, linkFor, thumbnailFor, youtubeId } from "@/lib/links";
import { formatSize, formatTime, parseTime } from "@/lib/time";
import { highlight, tokenize } from "@/lib/words";
import { fileNameFrom, qs } from "@/api/client";

describe("time", () => {
  it("formats seconds", () => {
    expect(formatTime(0)).toBe("0:00");
    expect(formatTime(75.9)).toBe("1:15");
    expect(formatTime(3725)).toBe("1:02:05");
    expect(formatTime(-4)).toBe("0:00");
    expect(formatTime(Number.NaN)).toBe("0:00");
  });
  it("parses times", () => {
    expect(parseTime("90")).toBe(90);
    expect(parseTime("2:30")).toBe(150);
    expect(parseTime("1:02:05")).toBe(3725);
    expect(parseTime("1h2m5s")).toBe(3725);
    expect(parseTime("")).toBeNull();
    expect(parseTime("abc")).toBeNull();
    expect(parseTime(undefined)).toBeNull();
  });
  it("formats sizes", () => {
    const u = { kb: "KB", mb: "MB", gb: "GB" };
    expect(formatSize(512, u)).toBe("1 KB");
    expect(formatSize(2_500_000, u)).toBe("2.5 MB");
    expect(formatSize(3_200_000_000, u)).toBe("3.2 GB");
  });
});

describe("cues", () => {
  const cues = [
    { start: 0, end: 2, src: "a" },
    { start: 2, end: 4, src: "b" },
    { start: 5, end: 7, src: "" },
    { start: 7, end: 9, src: "d" },
  ];
  it("finds the cue showing at a time", () => {
    expect(activeIndex(cues, 0)).toBe(0);
    expect(activeIndex(cues, 3.9)).toBe(1);
    expect(activeIndex(cues, 4.5)).toBe(-1); // between cues
    expect(activeIndex(cues, 8)).toBe(3);
    expect(activeIndex(cues, 20)).toBe(-1);
    expect(activeIndex([], 1)).toBe(-1);
  });
  it("finds the last started cue", () => {
    expect(lastStartedIndex(cues, -1)).toBe(-1);
    expect(lastStartedIndex(cues, 4.5)).toBe(1);
    expect(lastStartedIndex(cues, 4.96)).toBe(2); // 50 ms tolerance
    expect(lastStartedIndex(cues, 100)).toBe(3);
  });
  it("translates nearest lines first and skips empty or done ones", () => {
    expect(translationOrder(cues, () => false, 7.5)).toEqual([3, 1, 0]);
    expect(translationOrder(cues, (i) => i === 3, 7.5)).toEqual([1, 0]);
    expect(translationOrder(cues, () => false, 0, 1)).toEqual([0]);
  });
  it("builds the copy text", () => {
    const two = cues.slice(0, 2);
    const tr = (i: number) => ["أ", ""][i]!;
    expect(transcriptText(two, tr, "ar", formatTime)).toBe("0:00  أ\n0:02  b");
    expect(transcriptText(two, tr, "src", formatTime)).toBe("0:00  a\n0:02  b");
    expect(transcriptText(two, tr, "bi", formatTime)).toBe("0:00  a\nأ\n\n0:02  b");
  });
});

describe("words", () => {
  it("tokenizes tappable words and keeps punctuation", () => {
    const t = tokenize("Hello, world! It's 3D-ready.");
    expect(t.filter((x) => x.word).map((x) => (x.word ? x.lookup : ""))).toEqual(["Hello", "world", "It's"]);
    expect(t.map((x) => x.text).join("")).toBe("Hello, world! It's 3D-ready.");
  });
  it("highlights matches case-insensitively", () => {
    expect(highlight("Foo bar FOO", "foo")).toEqual([
      { text: "Foo", hit: true },
      { text: " bar ", hit: false },
      { text: "FOO", hit: true },
    ]);
    expect(highlight("abc", " ")).toEqual([{ text: "abc", hit: false }]);
  });
});

describe("links", () => {
  it("extracts YouTube ids", () => {
    expect(youtubeId("https://www.youtube.com/watch?v=lR931Iz8Z6U&t=10")).toBe("lR931Iz8Z6U");
    expect(youtubeId("https://youtu.be/lR931Iz8Z6U")).toBe("lR931Iz8Z6U");
    expect(youtubeId("youtube.com/shorts/lR931Iz8Z6U")).toBe("lR931Iz8Z6U");
    expect(youtubeId("lR931Iz8Z6U")).toBe("lR931Iz8Z6U");
    expect(youtubeId("https://vimeo.com/123")).toBeNull();
  });
  it("classifies what the user pasted", () => {
    expect(classifyLink("https://www.youtube.com/watch?v=lR931Iz8Z6U").kind).toBe("youtube");
    expect(classifyLink("https://www.youtube.com/watch?v=lR931Iz8Z6U&list=PL123").kind).toBe("youtube");
    expect(classifyLink("https://www.youtube.com/playlist?list=PL123").kind).toBe("playlist");
    expect(classifyLink("https://www.youtube.com/@freecodecamp").kind).toBe("channel");
    expect(classifyLink("media:0123456789ab").kind).toBe("media");
    expect(classifyLink("https://vimeo.com/76979871").kind).toBe("site");
    expect(classifyLink("vimeo.com/76979871")).toEqual({ kind: "site", link: "https://vimeo.com/76979871" });
    expect(classifyLink("hello there").kind).toBe("invalid");
    expect(classifyLink("").kind).toBe("invalid");
  });
  it("builds links and thumbnails", () => {
    expect(linkFor("abcdefghijk")).toBe("https://youtu.be/abcdefghijk");
    expect(linkFor("media:0123456789ab")).toBe("media:0123456789ab");
    expect(thumbnailFor("media:0123456789ab")).toBeNull();
    expect(thumbnailFor("abcdefghijk")).toContain("/vi/abcdefghijk/");
  });
});

describe("api helpers", () => {
  it("builds query strings", () => {
    expect(qs({ a: "x y", b: 2, c: true, d: false, e: undefined, f: null })).toBe("?a=x+y&b=2&c=1&d=0");
    expect(qs({})).toBe("");
  });
  it("reads file names from Content-Disposition", () => {
    expect(fileNameFrom("attachment; filename*=UTF-8''%D8%AA%D8%B1.srt")).toBe("تر.srt");
    expect(fileNameFrom('attachment; filename="subs.vtt"')).toBe("subs.vtt");
    expect(fileNameFrom(null)).toBeNull();
  });
});
