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
}

export interface DubEngineInit {
  media: DubMedia;
  loadPlan(from: number, to: number, opts: { urgent: boolean }): Promise<DubPlan>;
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
  readonly stats: { spoken: number; skipped: number; holds: number };
  start(): void;
  stop(): void;
  setOptions(o: DubOptions): void;
}

export declare const SPILL: number;
export declare const MAX_FIT: number;
export declare const MAX_EFFECTIVE: number;
export declare const HOLD_LAG: number;
export declare const READY_GRACE: number;
export declare const HOLD_MAX_MS: number;
export default DubEngine;
