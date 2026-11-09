/* Typed client for the local backend (docs/specs.md §6).
   Every call resolves with the success shape or throws an ApiError carrying the stable error code.
   A network failure (server closed) becomes code "NO_SERVER". */
import type {
  AiSettings,
  AiSettingsInput,
  Answer,
  BatchRequest,
  Cue,
  DubPlanResponse,
  DubRequest,
  Failure,
  Health,
  Job,
  LibraryItem,
  MediaItem,
  MediaJob,
  PronounceRule,
  Quality,
  SubFormat,
  SubMode,
  Summary,
  VideoCues,
  VocabItem,
  Voice,
  WhisperJob,
} from "./types";

export class ApiError extends Error {
  constructor(
    public code: string,
    message?: string,
    public status = 200,
  ) {
    super(message || code);
    this.name = "ApiError";
  }
}

export const errorCode = (e: unknown): string => (e instanceof ApiError ? e.code : "UNKNOWN");

type Query = Record<string, string | number | boolean | undefined | null>;

export function qs(q: Query): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (v === undefined || v === null) continue;
    p.set(k, typeof v === "boolean" ? (v ? "1" : "0") : String(v));
  }
  const s = p.toString();
  return s ? "?" + s : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError("NO_SERVER");
  }
  let body: unknown;
  try {
    body = await res.json();
  } catch {
    throw new ApiError(res.ok ? "BAD_JSON" : "HTTP_" + res.status, undefined, res.status);
  }
  const b = body as { ok?: boolean } & Partial<Failure>;
  if (!b || b.ok === false || !res.ok) {
    throw new ApiError(b?.code || "HTTP_" + res.status, b?.message, res.status);
  }
  return body as T;
}

const get = <T>(path: string, q: Query = {}, signal?: AbortSignal) => request<T>(path + qs(q), { signal });
const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
    signal,
  });

/** Downloads that answer with a file, or with JSON when they fail. */
async function fileRequest(path: string): Promise<{ blob: Blob; fileName: string | null; headers: Headers }> {
  let res: Response;
  try {
    res = await fetch(path);
  } catch {
    throw new ApiError("NO_SERVER");
  }
  const type = res.headers.get("content-type") || "";
  if (type.includes("json")) {
    const j = (await res.json().catch(() => ({}))) as Partial<Failure>;
    throw new ApiError(j.code || "HTTP_" + res.status, j.message, res.status);
  }
  if (!res.ok) throw new ApiError("HTTP_" + res.status, undefined, res.status);
  return { blob: await res.blob(), fileName: fileNameFrom(res.headers.get("content-disposition")), headers: res.headers };
}

export function fileNameFrom(cd: string | null): string | null {
  if (!cd) return null;
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      return decodeURIComponent(star[1]!.trim());
    } catch {
      /* fall through */
    }
  }
  const plain = cd.match(/filename="?([^";]+)"?/i);
  return plain ? plain[1]!.trim() : null;
}

export const api = {
  health: (signal?: AbortSignal) => get<Health>("/api/health", {}, signal),

  cues: (url: string, tl: string, fresh = false) => get<VideoCues>("/api/cues", { url, tl, fresh: fresh || undefined }),
  translate: (texts: string[], tl: string, sl = "auto") =>
    post<{ ok: true; map: Record<string, string> }>("/api/translate", { texts: texts.slice(0, 200), sl, tl }),
  editTranslation: (src: string, ar: string, tl: string) => post<{ ok: true }>("/api/translate/edit", { src, ar, tl }),

  subsUrl: (url: string, tl: string, mode: SubMode, format: SubFormat, save = true) =>
    "/api/subs" + qs({ url, tl, mode, format, save }),
  downloadSubs: (url: string, tl: string, mode: SubMode, format: SubFormat) => fileRequest(api.subsUrl(url, tl, mode, format, true)),

  voices: (lang: string) => get<{ ok: true; voices: Voice[] }>("/api/voices", { lang }),
  ttsUrl: (text: string, lang: string, voice = "", rate = 0) => "/api/tts" + qs({ text: text.slice(0, 1500), lang, voice, rate }),
  /** Synthesizes speech; resolves with a blob URL the caller must revoke. */
  async tts(text: string, lang: string, voice = "", rate = 0, signal?: AbortSignal): Promise<{ url: string; duration: number }> {
    let res: Response;
    try {
      res = await fetch(api.ttsUrl(text, lang, voice, rate), { signal });
    } catch (e) {
      if ((e as Error)?.name === "AbortError") throw e;
      throw new ApiError("NO_SERVER");
    }
    if (!(res.headers.get("content-type") || "").startsWith("audio")) {
      const j = (await res.json().catch(() => ({}))) as Partial<Failure>;
      throw new ApiError(j.code || "TTS_FAILED", j.message);
    }
    return { url: URL.createObjectURL(await res.blob()), duration: Number(res.headers.get("X-Audio-Duration")) || 0 };
  },

  dubPlan: (q: { url: string; tl: string; voice: string; from: number; to: number; urgent: boolean }, signal?: AbortSignal) =>
    get<DubPlanResponse>("/api/dubplan", q, signal),
  dubPlanForCues: (b: { cues: Pick<Cue, "start" | "end" | "src">[]; sl: string; tl: string; voice: string; from: number; to: number; urgent: boolean }) =>
    post<DubPlanResponse>("/api/dubplan/cues", b),

  startWhisper: (url: string, tl: string) => post<{ ok: true; id: string }>("/api/whisper/job", { url, tl }),
  whisperJob: (id: string) => get<WhisperJob>("/api/whisper/job", { id }),

  startDub: (b: DubRequest) => post<{ ok: true; id: string }>("/api/dub", b),
  dubJob: (id: string) => get<Job>("/api/dub/job", { id }),
  dubFileUrl: (id: string, dl = false) => "/api/dub/file" + qs({ id, dl }),

  startSubVideo: (b: { url: string; tl: string; mode: "ar" | "bi"; quality: Quality }) => post<{ ok: true; id: string }>("/api/subvideo", b),
  startBatch: (b: BatchRequest) => post<{ ok: true; id: string }>("/api/batch", b),
  cancelJob: (id: string) => post<{ ok: true }>("/api/job/cancel", { id }),
  jobs: () => get<{ ok: true; jobs: Job[] }>("/api/jobs"),

  library: () => get<{ ok: true; items: LibraryItem[] }>("/api/library"),
  libraryFileUrl: (kind: string, name: string, dl = false) => "/api/library/file" + qs({ kind, name, dl }),
  deleteLibraryFile: (kind: string, name: string) => post<{ ok: true }>("/api/library/delete", { kind, name }),

  /** Raw upload with progress (fetch has no upload progress). */
  upload(file: File, onProgress?: (fraction: number) => void): { promise: Promise<MediaItem & { ok: true }>; abort: () => void } {
    const xhr = new XMLHttpRequest();
    const promise = new Promise<MediaItem & { ok: true }>((resolve, reject) => {
      xhr.open("POST", "/api/media/upload" + qs({ name: file.name }));
      xhr.setRequestHeader("Content-Type", "application/octet-stream");
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
      xhr.onload = () => {
        let j: { ok?: boolean; code?: string; message?: string } = {};
        try {
          j = JSON.parse(xhr.responseText);
        } catch {
          /* handled below */
        }
        if (j.ok) resolve(j as MediaItem & { ok: true });
        else reject(new ApiError(j.code || "HTTP_" + xhr.status, j.message, xhr.status));
      };
      xhr.onerror = () => reject(new ApiError("NO_SERVER"));
      xhr.onabort = () => reject(new ApiError("CANCELLED"));
      xhr.send(file);
    });
    return { promise, abort: () => xhr.abort() };
  },
  fetchMedia: (url: string) => post<{ ok: true; id: string }>("/api/media/fetch", { url }),
  mediaJob: (id: string) => get<MediaJob>("/api/media/job", { id }),
  media: () => get<{ ok: true; items: MediaItem[] }>("/api/media"),
  mediaInfo: (id: string) => get<MediaItem & { ok: true }>("/api/media/info", { id }),
  mediaFileUrl: (id: string) => "/api/media/file" + qs({ id }),
  deleteMedia: (id: string) => post<{ ok: true }>("/api/media/delete", { id }),

  vocab: () => get<{ ok: true; items: VocabItem[] }>("/api/vocab"),
  addVocab: (b: Omit<VocabItem, "id" | "at">) => post<{ ok: true; item: VocabItem; duplicate: boolean }>("/api/vocab", b),
  deleteVocab: (id: string) => post<{ ok: true }>("/api/vocab/delete", { id }),
  vocabCsvUrl: "/api/vocab.csv",

  pronounce: () => get<{ ok: true; items: PronounceRule[] }>("/api/pronounce"),
  savePronounce: (items: PronounceRule[]) => post<{ ok: true; items: PronounceRule[] }>("/api/pronounce", { items }),
  previewPronounce: (text: string) => post<{ ok: true; text: string }>("/api/pronounce/preview", { text }),

  settings: () => get<{ ok: true; ai: AiSettings }>("/api/settings"),
  saveSettings: (ai: AiSettingsInput) => post<{ ok: true; ai: AiSettings }>("/api/settings", { ai }),
  testAi: () => post<{ ok: true; text: string; ms: number; model: string }>("/api/ai/test", {}),
  summary: (url: string, tl: string) => post<Summary>("/api/ai/summary", { url, tl }),
  ask: (url: string, tl: string, question: string) => post<Answer>("/api/ai/ask", { url, tl, question }),
};

export type Api = typeof api;
