/* localStorage with JSON and a namespace, plus a read-only fallback to the prototype's keys
   so people moving from the prototype keep their recent videos and positions. */
const NS = "tarjuman.";
const LEGACY = "ytar.";

export function load<T>(key: string, fallback: T, legacyKey?: string): T {
  try {
    let v = localStorage.getItem(NS + key);
    if (v == null && legacyKey) v = localStorage.getItem(LEGACY + legacyKey);
    return v == null ? fallback : (JSON.parse(v) as T);
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(NS + key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: preferences just won't persist */
  }
}
