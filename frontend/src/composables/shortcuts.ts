/* Keyboard shortcuts on the watch page, same keys as the prototype.
   Arabic keyboard layouts are covered too: each Latin key also matches the Arabic letter on the same key. */
import { onBeforeUnmount, onMounted } from "vue";

export type ShortcutId =
  | "play"
  | "next"
  | "prev"
  | "repeat"
  | "subs"
  | "bilingual"
  | "dub"
  | "learn"
  | "loop"
  | "bigger"
  | "smaller"
  | "fullscreen"
  | "cinema"
  | "search"
  | "help"
  | "close";

/** Shown in the shortcuts list. The right arrow moves forward (next line), as on every video player
 *  (YouTube included), whatever the page's direction. */
export const SHORTCUTS: { id: ShortcutId; keys: string[] }[] = [
  { id: "play", keys: ["K"] },
  { id: "next", keys: ["→"] },
  { id: "prev", keys: ["←"] },
  { id: "repeat", keys: ["R"] },
  { id: "subs", keys: ["C"] },
  { id: "bilingual", keys: ["B"] },
  { id: "dub", keys: ["D"] },
  { id: "learn", keys: ["L"] },
  { id: "loop", keys: ["O"] },
  { id: "bigger", keys: ["+"] },
  { id: "smaller", keys: ["−"] },
  { id: "fullscreen", keys: ["F"] },
  { id: "cinema", keys: ["T"] },
  { id: "search", keys: ["/"] },
  { id: "help", keys: ["?"] },
  { id: "close", keys: ["Esc"] },
];

/** key (lower-cased `KeyboardEvent.key`) → action. Arabic letters sit on the same physical keys. */
export const KEYMAP: Record<string, ShortcutId> = {
  k: "play",
  "ن": "play",
  arrowright: "next",
  arrowleft: "prev",
  r: "repeat",
  "ق": "repeat",
  c: "subs",
  "ؤ": "subs",
  b: "bilingual",
  "لا": "bilingual",
  d: "dub",
  "ي": "dub",
  l: "learn",
  "م": "learn",
  o: "loop",
  "خ": "loop",
  "+": "bigger",
  "=": "bigger",
  "-": "smaller",
  f: "fullscreen",
  "ب": "fullscreen",
  t: "cinema",
  "ف": "cinema",
  "/": "search",
  "?": "help",
  escape: "close",
};

export function shortcutFor(e: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey">): ShortcutId | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null;
  return KEYMAP[e.key.toLowerCase()] ?? null;
}

const isTyping = (t: EventTarget | null) =>
  t instanceof Element && !!t.closest("input, select, textarea, [contenteditable=''], [contenteditable='true']");

export function useShortcuts(handler: (id: ShortcutId, e: KeyboardEvent) => boolean | void) {
  function onKey(e: KeyboardEvent) {
    const id = shortcutFor(e);
    if (!id) return;
    if (id !== "close" && isTyping(e.target)) return;
    if (handler(id, e) !== false) e.preventDefault();
  }
  onMounted(() => document.addEventListener("keydown", onKey));
  onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
}
