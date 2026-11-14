export interface DubBlock {
  i: number;
  start: number;
  slot: number;
  rate?: number;
  synthRate?: number;
  playRate?: number;
  text: string;
  src?: string;
  srcStart?: number;
  end?: number;
  /** The video speed the server paced this sentence for (1 = normal). */
  speed?: number;
}

export interface DubMedia {
  time(): number;
  paused(): boolean;
  rate(): number;
  play(): void;
  pause(): void;
  /** 0..1 — the real volume, even while muted. */
  getVolume(): number;
  setVolume(v: number): void;
  /** Optional: change the video's speed. With it the engine slows the video slightly while the dub catches up. */
  setRate?(rate: number): void;
}

export interface DubPlan {
  blocks: DubBlock[];
  end?: number;
}

export interface DubAudio {
  url: string;
  duration: number;
}

export type DubState = "speaking" | "catching-up" | "waiting" | "buffering" | "idle" | "error";

export interface DubOptions {
  /** Hold the video briefly when the dub falls behind (default true). */
  wait?: boolean;
  /** Original volume while dubbing, 0..1 (default 0.15). */
  duck?: number;
  /** Slow the video slightly instead of letting the voice race, when `media.setRate` exists (default true). */
  flex?: boolean;
}

export interface DubEngineInit {
  media: DubMedia;
  loadPlan(from: number, to: number, opts: { urgent: boolean; speed: number }): Promise<DubPlan>;
  synth(block: DubBlock, rate: number): Promise<DubAudio>;
  onState?(state: DubState, info: { block?: DubBlock; message?: string }): void;
  options?: DubOptions;
  AudioCtor?: new (url: string) => HTMLAudioElement;
  now?(): number;
  revokeUrl?(url: string): void;
}

export declare class DubEngine {
  constructor(init: DubEngineInit);
  readonly running: boolean;
  readonly state: DubState;
  readonly stats: { spoken: number; skipped: number; holds: number; slowed: number };
  start(): void;
  stop(): void;
  setOptions(o: DubOptions): void;
  /** The user set the video's volume to v (0–1) while dubbing: ducks from it and restores it on stop. */
  userVolume(v: number): void;
}

export declare const SPILL: number;
export declare const MAX_FIT: number;
export declare const MAX_EFFECTIVE: number;
export declare const HOLD_LAG: number;
export declare const READY_GRACE: number;
export declare const HOLD_MAX_MS: number;
export default DubEngine;
