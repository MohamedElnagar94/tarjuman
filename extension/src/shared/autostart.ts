/**
 * Starting translation by itself on YouTube: never (the default), for every video, or only for the
 * channels the user listed. Stored as `autoStart` in chrome.storage.local.
 */
import { isYouTube, ytVideoId } from "./cues";

export type AutoMode = "off" | "always" | "channels";

export interface Channel {
  /** "@handle" (lower case) or "channel/UC…": what the channel's link on the watch page points to. */
  id: string;
  /** The name shown to the user. */
  name: string;
}

export interface AutoStart {
  mode: AutoMode;
  channels: Channel[];
}

export const DEFAULT_AUTO: Readonly<AutoStart> = Object.freeze({ mode: "off", channels: [] });
export const MAX_CHANNELS = 300;

/** The channel id in a channel link ("/@freeCodeCamp", "https://www.youtube.com/channel/UC…/videos"), or null. */
export function channelFromHref(href: string | null | undefined): string | null {
  const s = String(href || "").trim();
  if (!s) return null;
  let path = s;
  try {
    path = new URL(s, "https://www.youtube.com").pathname;
  } catch {
    return null;
  }
  let m = path.match(/^\/(@[^/?#]{1,100})/);
  if (m) {
    try {
      return decodeURIComponent(m[1]).toLowerCase();
    } catch {
      return m[1].toLowerCase();
    }
  }
  m = path.match(/^\/channel\/(UC[\w-]{10,40})/);
  return m ? "channel/" + m[1] : null;
}

/** What the user typed in the options page ("@name", "youtube.com/@name", a channel link) as an id. */
export function channelFromInput(input: string): string | null {
  const s = String(input || "").trim();
  if (!s) return null;
  if (/^@[^\s/?#]{1,100}$/.test(s)) return s.toLowerCase();
  if (/^UC[\w-]{10,40}$/.test(s)) return "channel/" + s;
  return channelFromHref(/^https?:\/\//i.test(s) ? s : s.startsWith("/") ? s : "https://" + s.replace(/^\/+/, ""));
}

/** Untrusted storage into valid rules. */
export function mergeAuto(raw: unknown): AutoStart {
  const o = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const mode: AutoMode = o.mode === "always" || o.mode === "channels" ? o.mode : "off";
  const seen = new Set<string>();
  const channels: Channel[] = [];
  for (const c of Array.isArray(o.channels) ? o.channels : []) {
    if (!c || typeof c !== "object") continue;
    const id = channelFromInput(String((c as Channel).id || ""));
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const name = String((c as Channel).name || "").trim().slice(0, 100) || id;
    channels.push({ id, name });
    if (channels.length >= MAX_CHANNELS) break;
  }
  return { mode, channels };
}

/** A video page that may start by itself: a watch or live video on YouTube. Not Shorts, which go by
 *  one after another as you scroll. */
export function isAutoStartPage(url: string): boolean {
  if (!isYouTube(url) || !ytVideoId(url)) return false;
  try {
    return !/^\/shorts\//.test(new URL(url).pathname);
  } catch {
    return false;
  }
}

export function hasChannel(rules: AutoStart, id: string | null | undefined): boolean {
  return !!id && rules.channels.some((c) => c.id === id);
}

/** Whether this video should start by itself. */
export function shouldAutoStart(rules: AutoStart, url: string, channelId?: string | null): boolean {
  if (rules.mode === "off" || !isAutoStartPage(url)) return false;
  if (rules.mode === "always") return true;
  return hasChannel(rules, channelId);
}

/** Adds or removes a channel. Adding one while auto-start is off turns on "only these channels". */
export function setChannel(rules: AutoStart, channel: Channel, on: boolean): AutoStart {
  const id = channelFromInput(channel.id);
  if (!id) return rules;
  const rest = rules.channels.filter((c) => c.id !== id);
  if (!on) return { ...rules, channels: rest };
  const name = String(channel.name || "").trim().slice(0, 100) || id;
  return { mode: rules.mode === "off" ? "channels" : rules.mode, channels: [...rest, { id, name }].slice(-MAX_CHANNELS) };
}
