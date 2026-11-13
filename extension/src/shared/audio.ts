/** Audio helpers for live mode: cutting tab audio into phrases at natural pauses. */

export function rms(f32: Float32Array, from = 0, to = f32.length): number {
  let sum = 0;
  for (let i = from; i < to; i++) sum += f32[i] * f32[i];
  return Math.sqrt(sum / Math.max(1, to - from));
}

export function downsampleTo16k(input: Float32Array, inputRate: number): Float32Array {
  if (inputRate === 16000) return input;
  const ratio = inputRate / 16000;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const s = Math.floor(i * ratio);
    const e = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0;
    for (let j = s; j < e; j++) sum += input[j];
    out[i] = e > s ? sum / (e - s) : 0;
  }
  return out;
}

export function bytesToB64(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000) as unknown as number[]);
  }
  return btoa(bin);
}

export function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

export function b64ToObjectUrl(b64: string, mime?: string): string {
  return URL.createObjectURL(new Blob([b64ToBytes(b64)], { type: mime || "audio/mpeg" }));
}

/** s16le PCM bytes: what /api/live/raw takes as its body. */
export function toPcm16(f32: Float32Array): Uint8Array {
  const i16 = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = Math.max(-1, Math.min(1, f32[i]));
    i16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return new Uint8Array(i16.buffer);
}

/** s16le PCM, base64: the format /api/live expects (apps before 3.1). */
export function toPcm16B64(f32: Float32Array): string {
  return bytesToB64(toPcm16(f32));
}

export interface ChunkerOptions {
  /** Never send less than this (seconds): Whisper needs context. */
  minChunk: number;
  /** Always cut at this length, even mid-speech, so the delay stays bounded. */
  maxChunk: number;
  /** A tail this long (seconds) below `silenceRms` counts as a pause. */
  pause: number;
  silenceRms: number;
  /** Chunks quieter than this overall are dropped (pure silence). */
  deadRms: number;
}

// Measured in the prototype: cutting at pauses between 2.5 and 6 s gives Whisper
// whole phrases and keeps the subtitle delay around 4–7 s.
export const CHUNK_DEFAULTS: ChunkerOptions = { minChunk: 2.5, maxChunk: 6, pause: 0.35, silenceRms: 0.006, deadRms: 0.0012 };

/** Collects audio frames and cuts them into phrases at natural pauses. */
export class Chunker {
  private chunks: Float32Array[] = [];
  private buffered = 0;
  readonly opts: ChunkerOptions;

  constructor(public rate: number, opts: Partial<ChunkerOptions> = {}) {
    this.opts = { ...CHUNK_DEFAULTS, ...opts };
  }

  get seconds() {
    return this.buffered / this.rate;
  }

  reset() {
    this.chunks = [];
    this.buffered = 0;
  }

  /**
   * Adds a frame. When it is time to cut, returns the finished chunk (at the input rate),
   * or `null` with the buffer cleared when the chunk was silence. Otherwise returns undefined.
   */
  push(data: Float32Array): Float32Array | null | undefined {
    this.chunks.push(new Float32Array(data));
    this.buffered += data.length;
    const secs = this.seconds;
    if (secs < this.opts.minChunk) return undefined;
    if (this.tailRms() < this.opts.silenceRms || secs >= this.opts.maxChunk) return this.flush();
    return undefined;
  }

  /** RMS over the last `pause` seconds. */
  tailRms(): number {
    const tailLen = Math.floor(this.opts.pause * this.rate);
    let sum = 0;
    let n = 0;
    for (let i = this.chunks.length - 1; i >= 0 && n < tailLen; i--) {
      const c = this.chunks[i];
      const take = Math.min(c.length, tailLen - n);
      sum += rms(c, c.length - take) ** 2 * take;
      n += take;
    }
    return Math.sqrt(sum / Math.max(1, n));
  }

  /** Returns the buffered audio and starts a new chunk; null when it was silence. */
  flush(): Float32Array | null {
    const out = new Float32Array(this.buffered);
    let off = 0;
    for (const c of this.chunks) {
      out.set(c, off);
      off += c.length;
    }
    this.reset();
    return rms(out) < this.opts.deadRms ? null : out;
  }
}
