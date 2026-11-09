import type { Settings } from "./settings";
import type { Health } from "./server";

export type Mode = "youtube" | "captions" | "live";

export interface RunState {
  active: boolean;
  mode: Mode | null;
  tabId: number | null;
  track?: number;
}

export interface TabInfo {
  id: number;
  url: string;
  youtube: boolean;
  protected: boolean;
  /** "https://site/*" for pages outside YouTube, else null. */
  origin: string | null;
  /** The extension may run on this site again after a reload (YouTube, or the site was granted). */
  siteGranted: boolean;
}

export interface Status {
  ok: true;
  state: RunState;
  settings: Settings;
  server: string | null;
  health: Health | null;
  override: string | null;
  tab: TabInfo | null;
  activeHere: boolean;
  version: string;
}

export interface Reply {
  ok: boolean;
  code?: string;
  message?: string;
  [k: string]: any;
}

/** Sends a message to the background. Never throws. */
export function send<T = Reply>(type: string, payload: Record<string, unknown> = {}): Promise<T> {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage({ type, ...payload }, (res) => {
        if (chrome.runtime.lastError) resolve({ ok: false, message: chrome.runtime.lastError.message } as T);
        else resolve((res || { ok: false }) as T);
      });
    } catch (e) {
      resolve({ ok: false, code: /context invalidated/i.test(String(e)) ? "INVALIDATED" : "SEND_FAILED", message: String(e) } as T);
    }
  });
}
