/**
 * Keys on the page while Tarjuman is translating. YouTube already uses k j l c f m t i ← → ↑ ↓ , . < >
 * 0–9 - + / and Shift+N/P, so these stay off them: Alt + arrows (as in the web app, → next and
 * ← previous), and the bracket keys as one-key alternatives.
 *
 * Keys are matched by their physical position (KeyboardEvent.code), so they work the same with an
 * Arabic keyboard layout, where "[" types "ج".
 */

export type ShortcutAction = "prev" | "next" | "repeat" | "subs" | "dub" | "earlier" | "later" | "resetTiming" | "transcript";

export interface KeyLike {
  code: string;
  altKey: boolean;
  shiftKey: boolean;
  ctrlKey: boolean;
  metaKey: boolean;
  isComposing?: boolean;
}

type Mods = "" | "alt";

const MAP: Record<string, Partial<Record<Mods, ShortcutAction>>> = {
  ArrowLeft: { alt: "prev" },
  ArrowRight: { alt: "next" },
  ArrowDown: { alt: "repeat" },
  BracketLeft: { "": "prev", alt: "earlier" },
  BracketRight: { "": "next", alt: "later" },
  Backslash: { "": "repeat", alt: "resetTiming" },
  IntlBackslash: { "": "repeat", alt: "resetTiming" },
  KeyS: { alt: "subs" },
  KeyV: { alt: "dub" },
  KeyT: { alt: "transcript" },
};

/** The action for a key press, or null when it isn't ours (or carries Ctrl, Cmd or Shift). */
export function shortcutFor(e: KeyLike): ShortcutAction | null {
  if (e.ctrlKey || e.metaKey || e.shiftKey || e.isComposing) return null;
  const mods: Mods = e.altKey ? "alt" : "";
  return MAP[e.code]?.[mods] ?? null;
}

/** The keys for each action, as shown in the options page and the toolbar's tooltips. */
export const SHORTCUT_KEYS: Record<ShortcutAction, string[]> = {
  prev: ["Alt+←", "["],
  next: ["Alt+→", "]"],
  repeat: ["Alt+↓", "\\"],
  subs: ["Alt+S"],
  dub: ["Alt+V"],
  transcript: ["Alt+T"],
  earlier: ["Alt+["],
  later: ["Alt+]"],
  resetTiming: ["Alt+\\"],
};

/** The order the options page lists them in. */
export const SHORTCUT_ORDER: ShortcutAction[] = ["prev", "next", "repeat", "subs", "dub", "transcript", "earlier", "later", "resetTiming"];

/** "Label (Alt+S)" for a tooltip. */
export const withKeys = (label: string, action: ShortcutAction) => `${label} (${SHORTCUT_KEYS[action].join(" / ")})`;

interface ElementLike {
  tagName?: string;
  isContentEditable?: boolean;
  type?: string;
  getAttribute?(name: string): string | null;
}

const TEXT_INPUTS = new Set(["", "text", "search", "email", "url", "tel", "password", "number", "date", "time", "datetime-local", "month", "week"]);

/** Whether a key press goes to something the user types into (a search box, YouTube's comment box…). */
export function isTypingTarget(el: ElementLike | null | undefined): boolean {
  if (!el || !el.tagName) return false;
  const tag = el.tagName.toUpperCase();
  if (tag === "TEXTAREA" || tag === "SELECT") return true;
  if (tag === "INPUT") return TEXT_INPUTS.has(String(el.type || "").toLowerCase());
  if (el.isContentEditable) return true;
  const role = el.getAttribute?.("role");
  return role === "textbox" || role === "searchbox" || role === "combobox";
}
