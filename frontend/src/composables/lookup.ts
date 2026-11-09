/* Tap an English word in the transcript or the subtitles: its meaning, its pronunciation, save it. */
import { reactive } from "vue";
import { api } from "@/api/client";
import { usePrefs } from "./prefs";
import { cues, pausePlayer, session, tr } from "./session";

export const lookup = reactive({
  open: false,
  word: "",
  sentence: "",
  sentenceTr: "",
  t: 0,
  meaning: "",
  status: "idle" as "idle" | "loading" | "ok" | "none" | "error",
  save: "idle" as "idle" | "saving" | "saved" | "duplicate" | "error",
  /** Where to anchor the popover (viewport coordinates of the word). */
  rect: { top: 0, bottom: 0, left: 0, right: 0, width: 0 },
});

let seq = 0;

export const srcLangCode = () => (session.srcLang && session.srcLang !== "auto" ? session.srcLang : "en");

export async function openLookup(word: string, cueIdx: number, el: Element): Promise<void> {
  const cue = cues.value[cueIdx];
  const r = el.getBoundingClientRect();
  const my = ++seq;
  pausePlayer();
  Object.assign(lookup, {
    open: true,
    word,
    sentence: cue?.src || "",
    sentenceTr: tr.value[cueIdx] || "",
    t: cue?.start || 0,
    meaning: "",
    status: "loading",
    save: "idle",
    rect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width },
  });
  try {
    const res = await api.translate([word], usePrefs().tl, srcLangCode());
    if (my !== seq) return;
    lookup.meaning = res.map[word] || "";
    lookup.status = lookup.meaning ? "ok" : "none";
  } catch {
    if (my === seq) lookup.status = "error";
  }
}

export function closeLookup(): void {
  seq++;
  lookup.open = false;
}

export async function saveLookup(): Promise<void> {
  if (!lookup.word || lookup.save === "saving") return;
  lookup.save = "saving";
  try {
    const r = await api.addVocab({
      word: lookup.word,
      tr: lookup.meaning,
      sentence: lookup.sentence,
      sentenceTr: lookup.sentenceTr,
      videoId: session.videoId,
      title: session.title,
      t: lookup.t,
    });
    lookup.save = r.duplicate ? "duplicate" : "saved";
    vocabVersion.n++;
  } catch {
    lookup.save = "error";
  }
}

/** Bumped when words are saved, so lists elsewhere can refresh. */
export const vocabVersion = reactive({ n: 0 });
