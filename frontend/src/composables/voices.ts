import { ref, watch } from "vue";
import { api } from "@/api/client";
import type { Voice } from "@/api/types";
import { usePrefs } from "./prefs";

const voices = ref<Voice[]>([]);
const loading = ref(false);
const failed = ref(false);
let watching = false;

async function load(lang: string): Promise<void> {
  loading.value = true;
  failed.value = false;
  try {
    voices.value = (await api.voices(lang)).voices || [];
  } catch {
    voices.value = [];
    failed.value = true;
  } finally {
    loading.value = false;
  }
  const prefs = usePrefs();
  if (prefs.voice !== "auto" && !voices.value.some((v) => v.id === prefs.voice)) prefs.voice = "auto";
}

/** Voices for the current target language. "auto" means: let the server pick (first voice live, matched to the speaker in MP4s). */
export function useVoices() {
  const prefs = usePrefs();
  if (!watching) {
    watching = true;
    watch(() => prefs.tl, (lang) => void load(lang), { immediate: true });
  }
  return { voices, loading, failed, reload: () => load(prefs.tl) };
}

/** The voice id sent to the live endpoints: "" lets the server use its default. */
export const liveVoiceId = (v: string) => (v === "auto" ? "" : v);

export { VOICE_SAMPLES } from "@/lib/voiceSamples";

let previewEl: HTMLAudioElement | null = null;

/** Plays a short audio clip from /api/tts, stopping any previous preview. */
export async function playTts(text: string, lang: string, voice = ""): Promise<void> {
  previewEl?.pause();
  const a = await api.tts(text, lang, voice, 0);
  const el = new Audio(a.url);
  previewEl = el;
  el.onended = el.onerror = () => URL.revokeObjectURL(a.url);
  await el.play();
}

/** A voice as a menu shows it: its name and accent, or that it works offline (and downloads once). */
export function voiceLabel(v: Voice, t: (k: string, p?: Record<string, unknown>) => string): string {
  if (v.engine === "supertonic") return `${v.name} · ${t("voice.offline")}${v.download ? ` (${t("voice.firstDownload", { size: v.download })})` : ""}`;
  return `${v.name} · ${v.accent}`;
}
