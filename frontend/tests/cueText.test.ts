import { describe, expect, it } from "vitest";
import { litWords, pieces, speakers, startsTurn } from "@/lib/cueText";

describe("caption line parts", () => {
  it("finds speaker turns", () => {
    expect(startsTurn(">> Red housing once more, sir.")).toBe(true);
    expect(startsTurn("- Who's there?")).toBe(true);
    expect(startsTurn("Emerald light within.")).toBe(false);
    expect(speakers([">> a", "b", ">> c", "d", ">> e"])).toEqual([0, 0, 1, 1, 0]);
  });

  it("turns sound tags into icons and keeps the words", () => {
    expect(pieces(">> Raising [music] it now.")).toEqual([
      { kind: "text", text: "Raising " },
      { kind: "tag", sound: "music", label: "music" },
      { kind: "text", text: " it now." },
    ]);
    expect(pieces("[تصفيق]")).toEqual([{ kind: "tag", sound: "applause", label: "تصفيق" }]);
    expect(pieces("♪ ♪")[0]).toEqual({ kind: "tag", sound: "music", label: "♪" });
    expect(pieces("see (page 4) here")).toEqual([{ kind: "text", text: "see (page 4) here" }]);
    expect(pieces("[inaudible] sorry")[0]).toEqual({ kind: "tag", sound: "other", label: "inaudible" });
  });

  it("lights words in step with the line", () => {
    expect(litWords("واحد اثنان ثلاثة أربعة", 0)).toBe(0);
    expect(litWords("واحد اثنان ثلاثة أربعة", 0.5)).toBe(2);
    expect(litWords("واحد اثنان ثلاثة أربعة", 2)).toBe(4);
  });
});
