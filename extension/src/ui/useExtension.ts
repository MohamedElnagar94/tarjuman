import { reactive, ref } from "vue";
import { mergeSettings, type Settings } from "@/shared/settings";
import { send, type Status } from "@/shared/messages";
import { b64ToObjectUrl } from "@/shared/audio";

export interface Voice {
  id: string;
  name: string;
  accent: string;
  gender?: string;
  engine?: string;
}

const VOICE_SAMPLE: Record<string, string> = {
  ar: "أهلًا بك! أنا الصوت الذي سيدبلج هذا الفيديو.",
  en: "Hi! I'm the voice that will dub this video.",
  fr: "Bonjour ! Je suis la voix de ce doublage.",
  es: "¡Hola! Soy la voz de este doblaje.",
  de: "Hallo! Ich bin die Stimme dieser Synchronisation.",
  tr: "Merhaba! Bu videoyu ben seslendireceğim.",
};

/** Settings, status and voices, shared by the popup and the options page. */
export function useExtension() {
  const settings = reactive<Settings>(mergeSettings(null));
  const status = ref<Status | null>(null);
  const loaded = ref(false);
  const voices = ref<Voice[]>([]);
  const previewing = ref(false);
  let previewAudio: HTMLAudioElement | null = null;

  async function refresh() {
    const st = await send<Status>("status");
    if (st && st.ok) {
      status.value = st;
      Object.assign(settings, mergeSettings(st.settings));
    } else {
      status.value = null;
    }
    loaded.value = true;
    return st;
  }

  async function update(patch: Partial<Settings>) {
    Object.assign(settings, mergeSettings(settings, patch));
    await send("set-settings", { settings: patch });
  }

  async function loadVoices() {
    const r = await send<{ ok: boolean; voices?: Voice[] }>("voices", { lang: settings.lang });
    if (!r || !r.ok || !r.voices) return (voices.value = []);
    voices.value = r.voices;
    // "" is the server's default voice (the first listed).
    const ids = r.voices.slice(1).map((v) => v.id);
    if (settings.voice && !ids.includes(settings.voice)) settings.voice = "";
  }

  /** Plays a short sample of the selected voice. Resolves false when the server couldn't speak. */
  async function previewVoice(): Promise<boolean> {
    previewing.value = true;
    try {
      previewAudio?.pause();
      const r = await send<any>("tts-fetch", { text: VOICE_SAMPLE[settings.lang] || VOICE_SAMPLE.ar, lang: settings.lang, voice: settings.voice });
      if (!r || !r.ok) return false;
      const url = b64ToObjectUrl(r.audio_b64, r.mime);
      previewAudio = new Audio(url);
      previewAudio.onended = () => URL.revokeObjectURL(url);
      await previewAudio.play();
      return true;
    } catch {
      return false;
    } finally {
      previewing.value = false;
    }
  }

  return { settings, status, loaded, voices, previewing, refresh, update, loadVoices, previewVoice };
}
