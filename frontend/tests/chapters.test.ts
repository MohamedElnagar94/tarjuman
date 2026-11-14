import { describe, expect, it } from "vitest";
import { chapterAt, chapterHeads, cleanChapters } from "../src/lib/chapters";

const CH = [
  { start: 0, title: "Intro" },
  { start: 60, title: "Setup" },
  { start: 150, title: "End" },
];
const CUES = [
  { start: 1, end: 20 },
  { start: 21, end: 59.8 },
  { start: 55, end: 75 }, // spans the start of "Setup"
  { start: 80, end: 100 },
  { start: 151, end: 160 },
];

describe("chapters", () => {
  it("finds the chapter playing", () => {
    expect(chapterAt(CH, 0)).toBe(0);
    expect(chapterAt(CH, 59.9)).toBe(1); // a hair early still counts: seeking lands just before
    expect(chapterAt(CH, 200)).toBe(2);
    expect(chapterAt([{ start: 10, title: "x" }], 3)).toBe(-1);
  });

  it("puts each heading above the right line", () => {
    expect([...chapterHeads(CH, CUES)]).toEqual([
      [0, 0],
      [2, 1],
      [4, 2],
    ]);
  });

  it("drops a chapter after the last line", () => {
    expect(chapterHeads([...CH, { start: 500, title: "Late" }], CUES).size).toBe(3);
  });

  it("cleans what the AI or a description gives", () => {
    const got = cleanChapters(
      [
        { start: 120, title: "B" },
        { start: 0, title: " A " },
        { start: 125, title: "too close" },
        { start: 50, title: "" },
        { start: 900, title: "after the end" },
      ],
      600,
    );
    expect(got).toEqual([
      { start: 0, title: "A" },
      { start: 120, title: "B" },
    ]);
    expect(cleanChapters([{ start: 0, title: "only one" }])).toEqual([]);
  });
});
