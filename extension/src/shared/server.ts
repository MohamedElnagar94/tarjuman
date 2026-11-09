/** Local server discovery. The app listens on the first free port in 4318–4327 (specs §2). */

export const FIRST_PORT = 4318;
export const PORTS = Array.from({ length: 10 }, (_, i) => FIRST_PORT + i);
export const DEFAULT_BASE = `http://127.0.0.1:${FIRST_PORT}`;

export interface Health {
  ok: true;
  app?: string;
  version?: string;
  port?: number;
  whisper?: { installed?: boolean; ready?: boolean; model?: string; error?: string };
  tts?: { installed?: boolean; ready?: boolean; edge?: boolean; piper?: boolean };
  ai?: { ready?: boolean; provider?: string; model?: string };
  [k: string]: unknown;
}

export interface Found {
  base: string;
  health: Health;
}

/** Accepts the Tarjuman server, and the prototype ("youtube-arabic") to ease testing. */
export function parseHealth(j: unknown): Health | null {
  if (!j || typeof j !== "object") return null;
  const o = j as Record<string, unknown>;
  if (o.ok !== true) return null;
  if (o.app === "tarjuman" || o.app === "youtube-arabic") return o as Health;
  return null;
}

const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);

/**
 * Validates a user-entered server address. Only loopback hosts are accepted:
 * they are the only hosts the extension has permission to reach.
 * Returns "http://host:port" or null.
 */
export function normalizeServerUrl(input: string): string | null {
  let s = String(input || "").trim();
  if (!s) return null;
  if (/^\d+$/.test(s)) s = `127.0.0.1:${s}`;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(s)) s = "http://" + s;
  let u: URL;
  try {
    u = new URL(s);
  } catch {
    return null;
  }
  if (u.protocol !== "http:") return null;
  if (!LOOPBACK.has(u.hostname)) return null;
  return `http://${u.hostname}${u.port ? ":" + u.port : ""}`;
}

/** Addresses to try, in order. An override replaces the port scan entirely. */
export function candidates(override?: string | null, last?: string | null): string[] {
  if (override) return [override];
  const scan = PORTS.map((p) => `http://127.0.0.1:${p}`);
  return last && scan.includes(last) ? [last, ...scan.filter((b) => b !== last)] : scan;
}

export type FetchLike = (url: string, init?: RequestInit) => Promise<{ ok: boolean; json(): Promise<unknown> }>;

export async function probe(base: string, fetchFn: FetchLike, ms = 1500): Promise<Health | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    const r = await fetchFn(`${base}/api/health`, { cache: "no-store", signal: ctrl.signal });
    if (!r.ok) return null;
    return parseHealth(await r.json());
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** Tries the last known address first, then scans every port at once and takes the lowest one that answers. */
export async function findServer(opts: { fetch: FetchLike; override?: string | null; last?: string | null; timeout?: number }): Promise<Found | null> {
  const ms = opts.timeout ?? 1500;
  const list = candidates(opts.override, opts.last);
  if (!opts.override && opts.last && list[0] === opts.last) {
    const h = await probe(opts.last, opts.fetch, ms);
    if (h) return { base: opts.last, health: h };
  }
  const results = await Promise.all(list.map(async (base) => ({ base, health: await probe(base, opts.fetch, ms) })));
  const hit = results.find((r) => r.health);
  return hit ? { base: hit.base, health: hit.health as Health } : null;
}
