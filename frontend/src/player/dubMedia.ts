import type { DubMedia } from "@tarjuman/dub-engine";
import { PlayerState, type Player } from "./types";

/** Lets the shared dub engine drive either player. `get` is read on every call so a swapped player is picked up. */
export function dubMedia(get: () => Player | null): DubMedia {
  return {
    time: () => get()?.getCurrentTime() ?? 0,
    paused: () => get()?.getPlayerState() !== PlayerState.Playing,
    rate: () => get()?.getPlaybackRate() || 1,
    play: () => get()?.playVideo(),
    pause: () => get()?.pauseVideo(),
    // The real volume even while muted; otherwise stopping the dub would restore the volume to 0.
    getVolume: () => (get()?.getVolume() ?? 100) / 100,
    setVolume: (v: number) => get()?.setVolume(Math.round(v * 100)),
  };
}
