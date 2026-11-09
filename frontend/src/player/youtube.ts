import type { Player } from "./types";

interface YTPlayerCtor {
  new (
    el: HTMLElement | string,
    opts: {
      videoId: string;
      playerVars?: Record<string, string | number>;
      events?: { onReady?: () => void; onError?: (e: { data: number }) => void; onStateChange?: (e: { data: number }) => void };
    },
  ): Player & { loadVideoById(id: string, start?: number): void; getIframe?(): HTMLIFrameElement };
}

declare global {
  interface Window {
    YT?: { Player: YTPlayerCtor };
    onYouTubeIframeAPIReady?: () => void;
  }
}

let loading: Promise<void> | null = null;

/** Loads the YouTube IFrame API once. Rejects if youtube.com can't be reached. */
export function ensureYouTubeApi(): Promise<void> {
  if (window.YT?.Player) return Promise.resolve();
  if (!loading) {
    loading = new Promise<void>((resolve, reject) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        prev?.();
        resolve();
      };
      const s = document.createElement("script");
      s.src = "https://www.youtube.com/iframe_api";
      s.async = true;
      s.onerror = () => {
        loading = null;
        s.remove();
        reject(new Error("YT_API"));
      };
      document.head.appendChild(s);
    });
  }
  return loading;
}

export interface YouTubeHandle {
  player: Player;
  /** YouTube error code (101/150 = the owner blocked embedding), if the player reported one. */
  error: number | null;
}

/** Creates a YouTube player inside `host`. Resolves when it is ready (or has reported an error). */
export async function createYouTubePlayer(
  host: HTMLElement,
  videoId: string,
  opts: { hl: string; onError?: (code: number) => void; onStateChange?: (state: number) => void },
): Promise<YouTubeHandle> {
  await ensureYouTubeApi();
  const mount = document.createElement("div");
  host.replaceChildren(mount);
  return new Promise<YouTubeHandle>((resolve) => {
    const handle: YouTubeHandle = { player: null as unknown as Player, error: null };
    handle.player = new window.YT!.Player(mount, {
      videoId,
      playerVars: { rel: 0, modestbranding: 1, cc_load_policy: 0, fs: 0, playsinline: 1, iv_load_policy: 3, hl: opts.hl },
      events: {
        onReady: () => resolve(handle),
        onError: (e) => {
          handle.error = e.data;
          opts.onError?.(e.data);
          resolve(handle);
        },
        onStateChange: (e) => opts.onStateChange?.(e.data),
      },
    });
  });
}

/** YouTube switches its own captions back on over ours (on load, after seeks, after ads), so keep
    unloading them: often for the first seconds, then every few seconds for the rest of the session. */
export function suppressNativeCaptions(player: Player, fastMs = 14000): () => void {
  const until = Date.now() + fastMs;
  const unload = () => {
    try {
      player.unloadModule?.("captions");
    } catch {
      /* not loaded yet */
    }
  };
  let slow: number | undefined;
  const fast = window.setInterval(() => {
    unload();
    if (Date.now() > until) {
      window.clearInterval(fast);
      slow = window.setInterval(unload, 3000);
    }
  }, 700);
  return () => {
    window.clearInterval(fast);
    window.clearInterval(slow);
  };
}
