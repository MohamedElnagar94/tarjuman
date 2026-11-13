/* What a caption line holds besides words: a change of speaker (YouTube writes ">>" or "- " at the
   start) and sound tags ("[Music]", "[تصفيق]", "♪"). Ported from the web app (frontend/src/lib/cueText.ts
   and lib/words.ts) so the transcript beside the video reads the same way. */

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

/** The line without the speaker mark at its start. */
export function stripTurn(text: string): string {
  return (text || "").replace(TURN, "");
}

function soundOf(label: string): SoundKind | null {
  for (const [kind, re] of SOUNDS) if (re.test(label)) return kind;
  return null;
}

/** The line without the speaker mark, cut into text and sound tags. A bracketed word that isn't a
 *  sound ("[inaudible]") is still a tag; a parenthesis that isn't a sound stays text. */
export function pieces(text: string): Piece[] {
  const s = stripTurn(text);
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

/** Where 0..1 the playhead is inside a line (for the fill of the line being said). */
export function lineProgress(start: number, end: number, t: number): number {
  return Math.max(0, Math.min(1, (t - start) / Math.max(0.3, end - start)));
}

/** A piece of a source line: plain text, or a word you can click to look up. */
export type Token = { text: string; word: false } | { text: string; word: true; lookup: string };

// Any script's letters (the original can be English, French, Spanish, Turkish…), with inner ' and -.
const WORD = /^([^\p{L}\p{N}]*)(\p{L}[\p{L}\p{M}\p{N}'’-]*)(.*)$/u;

/** Splits a line into clickable words, keeping spaces and punctuation as plain text. */
export function tokenize(line: string): Token[] {
  const out: Token[] = [];
  const push = (text: string) => {
    if (!text) return;
    const last = out[out.length - 1];
    if (last && !last.word) last.text += text;
    else out.push({ text, word: false });
  };
  for (const part of String(line || "").split(/(\s+)/)) {
    const m = part.match(WORD);
    if (!m) {
      push(part);
      continue;
    }
    push(m[1]);
    // "don't" stays whole; a trailing hyphen or apostrophe ("rock-'n'-") goes back to the punctuation.
    const word = m[2].replace(/['’-]+$/, "");
    out.push({ text: word, word: true, lookup: word.replace(/^['’]+/, "") });
    push(m[2].slice(word.length) + m[3]);
  }
  return out;
}

/** Splits text around case-insensitive matches of q, for search highlighting. */
export function highlight(text: string, q: string): { text: string; hit: boolean }[] {
  const s = String(text || "");
  const needle = q.trim().toLowerCase();
  if (!needle) return [{ text: s, hit: false }];
  const lo = s.toLowerCase();
  const out: { text: string; hit: boolean }[] = [];
  let from = 0;
  let at: number;
  while ((at = lo.indexOf(needle, from)) >= 0) {
    if (at > from) out.push({ text: s.slice(from, at), hit: false });
    out.push({ text: s.slice(at, at + needle.length), hit: true });
    from = at + needle.length;
  }
  if (from < s.length) out.push({ text: s.slice(from), hit: false });
  return out;
}

/** "1:05" or "1:02:03" for a time in seconds. */
export function clock(sec: number): string {
  const s = Math.max(0, Math.floor(sec || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}
