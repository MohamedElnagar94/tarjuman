/* Data shapes from docs/specs.md §5. */

export interface Cue {
  start: number;
  end: number;
  src: string;
  /** Target-language text (any language, the name is historical). */
  ar: string;
}

export interface VideoCues {
  ok: true;
  videoId: string;
  title: string;
  author: string;
  lengthSeconds: number;
  tl: string;
  alreadyTranslated: boolean;
  autoTranslated?: boolean;
  asr: boolean;
  whisper?: boolean;
  media?: boolean;
  srcLang: string;
  cues: Cue[];
}

export interface Voice {
  id: string;
  name: string;
  accent: string;
  gender: "m" | "f";
  engine: "edge" | "piper";
}

export interface DubBlock {
  i: number;
  start: number;
  slot: number;
  rate: number;
  synthRate: number;
  playRate: number;
  text: string;
  src: string;
  srcStart: number;
  end: number;
}

export interface DubPlanResponse {
  ok: true;
  from: number;
  to: number;
  total: number;
  end: number;
  blocks: DubBlock[];
}

export type JobType = "whisper" | "dub" | "subvideo" | "batch" | "fetch";
export type JobStatus = "queued" | "running" | "done" | "error" | "cancelled";

export interface DubInfo {
  sentences?: number;
  placed?: number;
  voice?: string;
  refit?: number;
  voiceRemoved?: boolean;
  multiSpeaker?: boolean;
  [k: string]: unknown;
}

export interface BatchItem {
  id: string;
  title: string;
  status: string;
  message: string;
}

export interface Job {
  ok: true;
  id: string;
  type: JobType;
  status: JobStatus;
  phase: string;
  progress: number;
  message: string;
  title: string;
  videoId: string;
  startedAt: number;
  size: number;
  fileName: string;
  fileUrl: string;
  dubInfo: DubInfo | null;
  what?: "subs" | "subvideo" | "dub";
  items?: BatchItem[];
}

export interface WhisperJob extends Job {
  srcLang: string;
  tl: string;
  cues?: Cue[];
}

export interface MediaItem {
  id: string;
  link: string;
  title: string;
  source: string;
  created: number;
  size: number;
  transcribed: boolean;
  /** What the file holds: a voice note or song is "audio". */
  kind: "audio" | "video";
  duration: number;
  /** The Whisper model that made the transcript ("" when none). */
  asr: string;
  lang: string;
  lines: number;
  /** A small waveform for the library (audio, once drawn). */
  wave?: number[];
}

export type AsrModelId = "tiny" | "base" | "small" | "medium" | "large-v3-turbo" | "large-v3";
export type AsrStyle = "general" | "msa" | "egyptian" | "gulf" | "levantine" | "maghrebi" | "none";

export interface AsrSettings {
  model: "auto" | AsrModelId;
  device: "auto" | "cpu" | "cuda";
  language: string;
  style: AsrStyle;
  quality: "accurate" | "fast";
  enhance: boolean;
  vad: boolean;
}

export interface AsrState {
  ok: true;
  settings: AsrSettings;
  hardware: { os: string; threads: number; cores: number; ramGb: number; cuda: number; gpu: string; vramGb: number; cublas: boolean };
  /** short: the model "auto" gives recordings up to 3 minutes. */
  recommended: { model: AsrModelId; device: "cpu" | "cuda"; short: AsrModelId; why: string[] };
  effective: { model: AsrModelId; device: "cpu" | "cuda"; beam: number; language: string | null; secondsPerMinute: number };
  models: { id: AsrModelId; size: number; ram: number; ar: number; secondsPerMinute: number; warning: string; downloaded: boolean }[];
  styles: AsrStyle[];
  languages: string[];
  status: {
    installed: boolean;
    ready: boolean;
    model: string;
    device: string;
    loading: null | { model: string; progress: number | null; seconds: number };
    error: string;
    fallback: string;
  };
}

export interface MediaJob extends Job {
  media: MediaItem | null;
}

export interface LibraryItem {
  kind: "dubbed" | "subs";
  name: string;
  size: number;
  mtime: number;
}

export interface VocabItem {
  id: string;
  word: string;
  tr: string;
  sentence: string;
  sentenceTr: string;
  videoId: string;
  title: string;
  t: number;
  at: number;
}

export interface PronounceRule {
  from: string;
  to: string;
}

export interface Health {
  ok: true;
  app: string;
  version: string;
  port: number;
  cache: number;
  providers: { googleCooling?: boolean; [k: string]: unknown };
  python: boolean;
  ffmpeg: boolean;
  whisper: { installed: boolean; ready: boolean; model?: string; error?: string };
  tts: { installed: boolean; ready: boolean; edge?: boolean; piper?: boolean; stats?: unknown };
  ai: { ready: boolean; provider: string; model: string; style: string };
  jobs: number;
  /** False on another device that has not been paired yet (it may only call /api/health). */
  paired?: boolean;
}

export type AiProvider = "anthropic" | "openai";
export type AiStyle = "msa" | "egyptian";

export interface AiSettings {
  enabled: boolean;
  provider: AiProvider;
  model: string;
  baseUrl: string;
  style: AiStyle;
  hasKey: boolean;
  keyHint: string;
  defaultModel: string;
  ready: boolean;
  stats?: unknown;
}

export interface AiSettingsInput {
  enabled: boolean;
  provider: AiProvider;
  model: string;
  baseUrl: string;
  style: AiStyle;
  /** Omit to keep the stored key, `null` to clear it. Never read back. */
  apiKey?: string | null;
}

export interface Summary {
  ok: true;
  summary: string;
  points: string[];
  chapters: { start: number; title: string }[];
}

export interface Answer {
  ok: true;
  answer: string;
  moments: number[];
}

export type SubMode = "ar" | "bi" | "src";
export type SubFormat = "srt" | "vtt" | "txt";
export type Quality = 480 | 720 | 1080;

export interface DubRequest {
  url: string;
  lang: string;
  voice: string;
  matchVoice?: boolean;
  bgVolume: number;
  embedSubs: boolean;
  burnSubs: boolean;
  removeVoice: boolean;
  quality: Quality;
}

export interface BatchRequest {
  url: string;
  what: "subs" | "subvideo" | "dub";
  tl: string;
  limit: number;
  voice: string;
  quality: Quality;
  bgVolume: number;
  embedSubs: boolean;
}

/** Every failure carries a stable `code` (specs §4). */
export interface Failure {
  ok: false;
  code: string;
  message?: string;
}
