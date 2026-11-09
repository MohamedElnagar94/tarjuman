import { PlayerState, type Player } from "./types";

/** The part of HTMLVideoElement the adapter touches (lets tests pass a plain object). */
export type VideoLike = Pick<
  HTMLVideoElement,
  "currentTime" | "paused" | "ended" | "readyState" | "playbackRate" | "volume" | "muted" | "duration" | "play" | "pause"
> & { removeAttribute?(name: string): void; load?(): void };

/** Wraps a <video> so it behaves like a YouTube IFrame player. */
export function html5Player(v: VideoLike, opts: { destroyElement?: boolean } = {}): Player {
  return {
    getCurrentTime: () => v.currentTime || 0,
    seekTo: (t: number) => {
      v.currentTime = Math.max(0, Number(t) || 0);
    },
    playVideo: () => {
      // play() rejects when autoplay is blocked or a pause interrupts it; both are normal here.
      void Promise.resolve(v.play()).catch(() => {});
    },
    pauseVideo: () => v.pause(),
    getPlayerState: () =>
      v.ended ? PlayerState.Ended : v.paused ? PlayerState.Paused : v.readyState < 3 ? PlayerState.Buffering : PlayerState.Playing,
    setPlaybackRate: (r: number) => {
      v.playbackRate = r;
    },
    getPlaybackRate: () => v.playbackRate || 1,
    getVolume: () => v.volume * 100,
    setVolume: (x: number) => {
      v.volume = Math.max(0, Math.min(1, x / 100));
    },
    isMuted: () => v.muted,
    getDuration: () => (Number.isFinite(v.duration) ? v.duration : 0),
    unloadModule() {},
    destroy() {
      v.pause();
      if (opts.destroyElement) {
        v.removeAttribute?.("src");
        v.load?.();
      }
    },
  };
}
