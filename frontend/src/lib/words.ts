/** A piece of a source line: plain text, or a word you can tap to look up. */
export type Token = { text: string; word: false } | { text: string; word: true; lookup: string };

const WORD = /^([^A-Za-z0-9']*)([A-Za-z][A-Za-z0-9'-]*)(.*)$/;

/** Splits an English line into tappable words, keeping spaces and punctuation as plain text. */
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
    push(m[1]!);
    out.push({ text: m[2]!, word: true, lookup: m[2]!.replace(/^'+|'+$/g, "") });
    push(m[3]!);
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
