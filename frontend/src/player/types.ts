/** YouTube IFrame player states. */
export const PlayerState = {
  Unstarted: -1,
  Ended: 0,
  Playing: 1,
  Paused: 2,
  Buffering: 3,
  Cued: 5,
} as const;

/**
 * The subset of the YouTube IFrame API the app uses. A YouTube player satisfies it as is;
 * local videos (`media:` links) get an HTML5 adapter with the same methods, so everything
 * else (sync, dub, learning mode, shortcuts) works the same on both.
 */
export interface Player {
  getCurrentTime(): number;
  seekTo(seconds: number, allowSeekAhead?: boolean): void;
  playVideo(): void;
  pauseVideo(): void;
  getPlayerState(): number;
  setPlaybackRate(rate: number): void;
  getPlaybackRate(): number;
  /** 0..100 */
  getVolume(): number;
  setVolume(v: number): void;
  isMuted(): boolean;
  getDuration(): number;
  unloadModule?(name: string): void;
  destroy(): void;
}
