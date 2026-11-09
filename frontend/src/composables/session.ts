/* The video being watched. One session at a time, shared by the player, the transcript and every panel. */
import { computed, markRaw, reactive, ref, shallowRef } from "vue";
import { api, ApiError, errorCode } from "@/api/client";
import type { Cue, VideoCues, WhisperJob } from "@/api/types";
import { errText, i18n } from "@/i18n";
import { activeIndex, lastStartedIndex, translationOrder } from "@/lib/cues";
import { isMediaId } from "@/lib/links";
import { formatTime } from "@/lib/time";
import { PlayerState, type Player } from "@/player/types";
import { pollJob, type JobPoll } from "./jobs";
import { usePrefs } from "./prefs";
import { getPosition, savePosition, useRecent } from "./recent";
import { toast } from "./toast";

export type Phase = "idle" | "loading" | "whisper" | "ready" | "error";

const t = (k: string, p?: Record<string, unknown>) => i18n.global.t(k, p ?? {});
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const session = reactive({
  /** The link the API is called with: a YouTube URL/id or `media:<id>`. */
  link: "",
  videoId: "",
  title: "",
  author: "",
  lengthSeconds: 0,
  srcLang: "auto",
  tl: "ar",
  already: false,
  autoTranslated: false,
  asr: false,
  whisper: false,
  phase: "idle" as Phase,
  error: { code: "", message: "" },
  /** Player is created and can be controlled. */
  ready: false,
  playing: false,
  /** YouTube player error code (101/150: embedding blocked by the owner). */
  playerError: null as number | null,
  curIdx: -1,
  time: 0,
  translating: false,
  translateFailed: 0,
  whisperJob: null as null | { progress: number; phase: string; status: string },
  /** Set by the live dub controller; learning mode stays out of the way while it runs. */
  dubOn: false,
});

/** Cues are big and never mutated in place: keep them out of deep reactivity. */
export const cues = shallowRef<Cue[]>([]);
/** Translations by cue index ("" = not yet). Reactive per index so a row repaints alone. */
export const tr = ref<string[]>([]);
/** Lines the user corrected in this session. */
export const edited = reactive(new Set<number>());

let tries: number[] = [];
let gen = 0;
let player: Player | null = null;
let ticker: number | undefined;
let whisperPoll: JobPoll<WhisperJob> | null = null;
let pendingSeek: number | null = null;
let learnFrom = -1;
let loopCue = -1;
let lastSavedAt = 0;

export const translatedCount = computed(() => tr.value.reduce((n, s) => n + (s ? 1 : 0), 0));
export const sourceCount = computed(() => cues.value.reduce((n, c) => n + (c.src ? 1 : 0), 0));

export function getPlayer(): Player | null {
  return player;
}

export function now(): number {
  try {
    return session.ready && player ? player.getCurrentTime() : 0;
  } catch {
    return 0;
  }
}

/* ---------------- loading ---------------- */

/** Loads captions for a link. `seek` is applied once the player is ready (vocabulary "go to sentence"). */
export async function loadVideo(link: string, opts: { seek?: number | null } = {}): Promise<void> {
  const prefs = usePrefs();
  const my = ++gen;
  stopWhisper();
  pendingSeek = opts.seek ?? null;
  session.link = link;
  session.phase = "loading";
  session.error = { code: "", message: "" };
  try {
    const d = await api.cues(link, prefs.tl);
    if (my !== gen) return;
    applyCues(link, d);
  } catch (e) {
    if (my !== gen) return;
    const code = errorCode(e);
    if (code === "NO_CAPTIONS") {
      session.phase = "whisper";
      session.whisperJob = null;
      // Keep what we know about the video for the "no captions" screen.
      session.videoId = isMediaId(link) ? link : "";
      return;
    }
    session.phase = "error";
    session.error = { code, message: e instanceof ApiError ? e.message : String(e) };
  }
}

function applyCues(link: string, d: Omit<VideoCues, "ok">): void {
  gen++;
  session.link = link;
  session.videoId = d.videoId;
  session.title = d.title || "";
  session.author = d.author || "";
  session.lengthSeconds = d.lengthSeconds || 0;
  session.srcLang = d.srcLang || "auto";
  session.tl = d.tl || usePrefs().tl;
  session.already = !!d.alreadyTranslated;
  session.autoTranslated = !!d.autoTranslated;
  session.asr = !!d.asr;
  session.whisper = !!d.whisper;
  session.curIdx = -1;
  session.translateFailed = 0;
  const list = Object.freeze((d.cues || []).map((c) => Object.freeze({ ...c })));
  cues.value = list as Cue[];
  tr.value = list.map((c) => c.ar || "");
  tries = list.map(() => 0);
  edited.clear();
  learnFrom = -1;
  loopCue = -1;
  session.phase = "ready";
  useRecent().remember({ videoId: d.videoId, title: d.title, lengthSeconds: d.lengthSeconds });
  document.title = (d.title ? d.title + " | " : "") + t("app.name");
  if (!session.already) void translateLoop();
}

/* ---------------- Whisper (no captions) ---------------- */

export async function startWhisper(): Promise<void> {
  const link = session.link;
  const my = gen;
  session.whisperJob = { progress: 0, phase: t("watch.whisper.starting"), status: "queued" };
  let id: string;
  try {
    ({ id } = await api.startWhisper(link, usePrefs().tl));
  } catch (e) {
    session.whisperJob = null;
    session.error = { code: errorCode(e), message: (e as Error).message };
    return;
  }
  whisperPoll = pollJob(
    () => api.whisperJob(id),
    (j) => {
      if (my === gen) session.whisperJob = { progress: j.progress || 0, phase: j.phase || "", status: j.status };
    },
  );
  try {
    const j = await whisperPoll.done;
    if (my !== gen) return;
    if (j.status === "done") {
      applyCues(link, {
        videoId: j.videoId,
        title: j.title,
        author: "",
        lengthSeconds: 0,
        tl: j.tl,
        alreadyTranslated: false,
        asr: true,
        whisper: true,
        srcLang: j.srcLang || "auto",
        cues: j.cues || [],
      });
    } else {
      session.whisperJob = null;
      session.error = { code: j.status === "cancelled" ? "CANCELLED" : "WHISPER_FAILED", message: j.message };
    }
  } catch (e) {
    if (my === gen) {
      session.whisperJob = null;
      session.error = { code: errorCode(e), message: (e as Error).message };
    }
  }
}

function stopWhisper(): void {
  whisperPoll?.stop();
  whisperPoll = null;
  session.whisperJob = null;
}

/* ---------------- translation ---------------- */

/** Translates the lines nearest the playhead first, 40 at a time, three tries per line. */
async function translateLoop(): Promise<void> {
  if (session.translating) return;
  const my = gen;
  session.translating = true;
  let failStreak = 0;
  try {
    while (my === gen) {
      const batch = translationOrder(cues.value, (i) => !!tr.value[i] || (tries[i] || 0) >= 3, now());
      if (!batch.length) break;
      let map: Record<string, string> | null = null;
      try {
        map = (await api.translate(batch.map((i) => cues.value[i]!.src), session.tl, session.srcLang || "auto")).map;
      } catch {
        map = null;
      }
      if (my !== gen) return;
      if (!map) {
        if (++failStreak >= 4) {
          toast(t("watch.translate.unavailable"), { tone: "danger" });
          break;
        }
        await sleep(900 * failStreak);
        continue;
      }
      failStreak = 0;
      for (const i of batch) {
        const text = map[cues.value[i]!.src];
        if (text) tr.value[i] = text;
        else tries[i] = (tries[i] || 0) + 1;
      }
    }
  } finally {
    if (my === gen) {
      session.translating = false;
      session.translateFailed = tries.filter((n, i) => n >= 3 && !tr.value[i]).length;
    }
  }
}

export function retryTranslation(): void {
  tries = tries.map(() => 0);
  session.translateFailed = 0;
  void translateLoop();
}

/** Saves a correction; the server applies it to subtitles, downloads and the dub from now on. */
export async function editLine(i: number, text: string): Promise<void> {
  const c = cues.value[i];
  if (!c) return;
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean === (tr.value[i] || "")) return;
  const before = tr.value[i] || "";
  tr.value[i] = clean;
  edited.add(i);
  try {
    await api.editTranslation(c.src, clean, session.tl);
    toast(t("watch.edit.saved"), { tone: "ok" });
  } catch (e) {
    tr.value[i] = before;
    edited.delete(i);
    toast(t("watch.edit.failed") + " " + errText(errorCode(e)), { tone: "danger" });
  }
}

/* ---------------- player ---------------- */

/** Called by the player stage once a player (YouTube or HTML5) is ready. */
export function attachPlayer(p: Player, onReady?: () => void): void {
  player = markRaw(p);
  session.ready = true;
  window.clearInterval(ticker);
  ticker = window.setInterval(tick, 120);
  // The YouTube player needs a moment after onReady before it honours seek and rate.
  window.setTimeout(() => {
    if (player !== p) return;
    applySpeed();
    if (pendingSeek != null) {
      seekTo(pendingSeek, false);
      pendingSeek = null;
    } else resumePosition();
    onReady?.();
  }, 600);
}

export function detachPlayer(): void {
  window.clearInterval(ticker);
  ticker = undefined;
  if (player && session.videoId) {
    try {
      savePosition(session.videoId, player.getCurrentTime(), player.getDuration());
    } catch {
      /* player already gone */
    }
  }
  player = null;
  session.ready = false;
  session.playing = false;
}

/** Leaving the watch page. */
export function endSession(): void {
  gen++;
  stopWhisper();
  detachPlayer();
  session.phase = "idle";
  session.link = "";
}

function tick(): void {
  if (!player || !session.ready) return;
  let state: number;
  try {
    state = player.getPlayerState();
    session.time = player.getCurrentTime();
  } catch {
    return;
  }
  session.playing = state === PlayerState.Playing;
  if (!cues.value.length) return;
  const i = activeIndex(cues.value, session.time);
  loopTick(i);
  if (i !== session.curIdx) {
    learnTick(i);
    session.curIdx = i;
  }
  trackPosition();
}

/** Learning mode: pause when a sentence ends, so you can read it before the next one. */
function learnTick(i: number): void {
  const prefs = usePrefs();
  if (!prefs.learn || session.dubOn || !player) {
    learnFrom = i;
    return;
  }
  if (learnFrom >= 0 && i !== learnFrom && session.playing) player.pauseVideo();
  learnFrom = i;
}

/** Repeat sentence: jump back to the start of the last line once it ends. */
function loopTick(i: number): void {
  if (i >= 0) loopCue = i;
  if (!usePrefs().loop || loopCue < 0 || !player || !session.playing) return;
  const c = cues.value[loopCue];
  if (c && session.time >= c.end - 0.05) player.seekTo(c.start + 0.01, true);
}

export function armLoop(): void {
  loopCue = session.curIdx;
}

function trackPosition(): void {
  if (!player || !session.videoId || Date.now() - lastSavedAt < 5000) return;
  lastSavedAt = Date.now();
  savePosition(session.videoId, session.time, player.getDuration());
}

function resumePosition(): void {
  const at = getPosition(session.videoId);
  if (!at || !player) return;
  player.seekTo(at, true);
  toast(t("watch.resumed", { time: formatTime(at) }), {
    action: { label: t("watch.fromStart"), run: () => player?.seekTo(0, true) },
  });
}

export function applySpeed(): void {
  try {
    player?.setPlaybackRate(usePrefs().speed || 1);
  } catch {
    /* not ready */
  }
}

export function seekTo(sec: number, play = true): void {
  if (!player || !session.ready) return;
  player.seekTo(Math.max(0, sec), true);
  if (play) player.playVideo();
}

export function seekToCue(i: number): void {
  const c = cues.value[i];
  if (c) seekTo(c.start + 0.01);
}

export function togglePlay(): void {
  if (!player) return;
  if (player.getPlayerState() === PlayerState.Playing) player.pauseVideo();
  else player.playVideo();
}

export function pausePlayer(): void {
  if (player && player.getPlayerState() === PlayerState.Playing) player.pauseVideo();
}

export function stepLine(delta: -1 | 0 | 1): void {
  if (!cues.value.length) return;
  const cur = lastStartedIndex(cues.value, now());
  seekToCue(Math.min(cues.value.length - 1, Math.max(0, cur + delta)));
}
