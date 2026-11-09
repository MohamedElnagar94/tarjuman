export type LinkKind = "youtube" | "media" | "playlist" | "channel" | "site" | "invalid";

const YT_HOST = /(^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com)$/i;

/** The 11-character video id of a YouTube link or bare id, or null. */
export function youtubeId(input: string): string | null {
  const s = String(input || "").trim();
  if (/^[\w-]{11}$/.test(s)) return s;
  let u: URL;
  try {
    u = new URL(/^https?:\/\//i.test(s) ? s : "https://" + s);
  } catch {
    return null;
  }
  if (!YT_HOST.test(u.hostname)) return null;
  if (/youtu\.be$/i.test(u.hostname)) {
    const id = u.pathname.slice(1).split("/")[0] || "";
    return /^[\w-]{11}$/.test(id) ? id : null;
  }
  const v = u.searchParams.get("v");
  if (v && /^[\w-]{11}$/.test(v)) return v;
  const m = u.pathname.match(/^\/(?:embed|shorts|live|v)\/([\w-]{11})/);
  return m ? m[1]! : null;
}

/** What the user pasted, and so where it goes: the player, the batch form, or a download from another site. */
export function classifyLink(input: string): { kind: LinkKind; link: string } {
  const link = String(input || "").trim();
  if (!link) return { kind: "invalid", link };
  if (/^media:[0-9a-f]{12}$/i.test(link)) return { kind: "media", link };
  if (/^[\w-]{11}$/.test(link)) return { kind: "youtube", link };
  const withScheme = /^https?:\/\//i.test(link) ? link : /^[\w.-]+\.[a-z]{2,}(\/|$)/i.test(link) ? "https://" + link : "";
  if (!withScheme) return { kind: "invalid", link };
  let u: URL;
  try {
    u = new URL(withScheme);
  } catch {
    return { kind: "invalid", link };
  }
  if (YT_HOST.test(u.hostname)) {
    const hasVideo = !!youtubeId(withScheme);
    if (!hasVideo && u.searchParams.get("list")) return { kind: "playlist", link: withScheme };
    if (/^\/(@|channel\/|c\/|user\/)/.test(u.pathname)) return { kind: "channel", link: withScheme };
    return hasVideo ? { kind: "youtube", link: withScheme } : { kind: "invalid", link };
  }
  return { kind: "site", link: withScheme };
}

export const isMediaId = (id: string | null | undefined) => String(id || "").startsWith("media:");

/** A link that reopens this video later (recent list, vocabulary "go to sentence"). */
export const linkFor = (videoId: string) => (isMediaId(videoId) ? videoId : "https://youtu.be/" + videoId);

export const thumbnailFor = (videoId: string) => (isMediaId(videoId) ? null : `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`);
