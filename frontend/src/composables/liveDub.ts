/* Live dubbing inside the app, driven by the shared engine (docs/specs.md §7). */
import { reactive } from "vue";
import { DubEngine, type DubState } from "@tarjuman/dub-engine";
import { api } from "@/api/client";
import { i18n } from "@/i18n";
import { dubMedia } from "@/player/dubMedia";
import { usePrefs } from "./prefs";
import { getPlayer, session } from "./session";
import { toast } from "./toast";
import { liveVoiceId } from "./voices";

export const liveDub = reactive({
  on: false,
  state: "idle" as DubState,
  sentence: "",
});

let engine: DubEngine | null = null;

export function startLiveDub(): void {
  const prefs = usePrefs();
  if (!session.ready || !getPlayer() || !session.link) {
    toast(i18n.global.t("dub.live.needPlayer"));
    return;
  }
  stopLiveDub(false);
  const url = session.link;
  const tl = session.tl;
  const voice = liveVoiceId(prefs.voice);
  engine = new DubEngine({
    media: dubMedia(getPlayer),
    loadPlan: async (from, to, { urgent }) => api.dubPlan({ url, tl, voice, from, to, urgent }),
    synth: (b, rate) => api.tts(b.text, tl, voice, rate),
    onState: (state, info) => {
      liveDub.state = state;
      if (info.block) liveDub.sentence = info.block.text;
    },
    options: { wait: prefs.dubWait, duck: prefs.bgVol },
  });
  engine.start();
  liveDub.on = true;
  session.dubOn = true;
  // The engine holds the video until the first sentence is ready, then plays it.
  liveDub.state = "buffering";
  if (!prefs.liveDub) prefs.liveDub = true;
}

/** `remember=false` keeps the preference (used when switching videos or restarting with a new voice). */
export function stopLiveDub(remember = true): void {
  engine?.stop();
  engine = null;
  liveDub.on = false;
  liveDub.state = "idle";
  liveDub.sentence = "";
  session.dubOn = false;
  if (remember) usePrefs().liveDub = false;
}

export function toggleLiveDub(): void {
  if (liveDub.on) stopLiveDub();
  else startLiveDub();
}

export function restartLiveDub(): void {
  if (!liveDub.on) return;
  stopLiveDub(false);
  startLiveDub();
}

export function setDubOptions(o: { wait?: boolean; duck?: number }): void {
  engine?.setOptions(o);
}

/** Warm the server up for the first sentences while the player is still loading. */
export function prewarmDub(): void {
  const prefs = usePrefs();
  if (!prefs.liveDub || !session.link) return;
  api.dubPlan({ url: session.link, tl: session.tl, voice: liveVoiceId(prefs.voice), from: 0, to: 12, urgent: false }).catch(() => {});
}
