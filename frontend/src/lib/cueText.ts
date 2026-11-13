/* What a caption line holds besides words: a change of speaker (YouTube writes ">>" or "- " at the
   start) and sound tags ("[Music]", "[تصفيق]", "♪"). The transcript shows them as a speaker mark and
   small icons instead of raw symbols. */

export type SoundKind = "music" | "applause" | "laughter" | "other";
export type Piece = { kind: "text"; text: string } | { kind: "tag"; sound: SoundKind; label: string };

const TURN = /^\s*(?:>>+\s*|-\s+|–\s+|—\s+)/;
const TAG = /\[([^\]\n]{1,40})\]|\(([^)\n]{1,30})\)|♪+|♫+/g;
const SOUNDS: [SoundKind, RegExp][] = [
  ["music", /music|موسيق|موسيقى|♪|♫|song|singing|أغني/i],
  ["applause", /applause|clapping|cheer|تصفيق|هتاف/i],
  ["laughter", /laugh|chuckl|ضحك/i],
];

/** Whether the line starts a new speaker's turn. */
export function startsTurn(text: string): boolean {
  return TURN.test(text || "");
}

function soundOf(label: string): SoundKind | null {
  for (const [kind, re] of SOUNDS) if (re.test(label)) return kind;
  return null;
}

/** The line without the speaker mark, cut into text and sound tags. A bracketed word that isn't a
 *  sound ("[inaudible]") is still a tag; a parenthesis that isn't a sound stays text. */
export function pieces(text: string): Piece[] {
  const s = (text || "").replace(TURN, "");
  const out: Piece[] = [];
  let last = 0;
  for (const m of s.matchAll(TAG)) {
    const raw = m[0];
    const label = (m[1] ?? m[2] ?? raw).trim();
    const sound = raw.startsWith("♪") || raw.startsWith("♫") ? "music" : soundOf(label);
    if (m[2] !== undefined && !sound) continue; // an ordinary parenthesis
    if (m.index! > last) out.push({ kind: "text", text: s.slice(last, m.index) });
    out.push({ kind: "tag", sound: sound ?? "other", label });
    last = m.index! + raw.length;
  }
  if (last < s.length) out.push({ kind: "text", text: s.slice(last) });
  return out.filter((p) => p.kind === "tag" || p.text.trim() !== "" || out.length === 1);
}

/** The speaker of each line: 0 or 1, switching on every line that starts a turn. */
export function speakers(lines: string[]): number[] {
  let who = 0;
  let seen = false;
  return lines.map((l) => {
    if (startsTurn(l)) {
      if (seen) who = 1 - who;
      seen = true;
    }
    return who;
  });
}

/** Words of a translated line lit so far, for a progress fraction 0..1 (a reading guide, not exact). */
export function litWords(text: string, fraction: number): number {
  const n = (text || "").split(/\s+/).filter(Boolean).length;
  return Math.max(0, Math.min(n, Math.ceil(n * Math.max(0, Math.min(1, fraction)))));
}
