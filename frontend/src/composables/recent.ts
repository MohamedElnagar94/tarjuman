import { ref } from "vue";
import { load, save } from "@/lib/storage";
import { linkFor } from "@/lib/links";

export interface RecentItem {
  videoId: string;
  title: string;
  url: string;
  at: number;
  lengthSeconds?: number;
}

const recent = ref<RecentItem[]>(load<RecentItem[]>("recent", [], "recent").filter((r) => r && r.videoId));

export function useRecent() {
  return {
    recent,
    remember(d: { videoId: string; title: string; lengthSeconds?: number }) {
      const list = recent.value.filter((r) => r.videoId !== d.videoId);
      list.unshift({ videoId: d.videoId, title: d.title, url: linkFor(d.videoId), at: Date.now(), lengthSeconds: d.lengthSeconds });
      recent.value = list.slice(0, 12);
      save("recent", recent.value);
    },
    forget(videoId: string) {
      recent.value = recent.value.filter((r) => r.videoId !== videoId);
      save("recent", recent.value);
    },
  };
}

/* "Continue where you left off": positions per video, at most 60 kept. */
type Positions = Record<string, number>;

export function getPosition(videoId: string): number | undefined {
  return load<Positions>("pos", {}, "pos")[videoId];
}

export function savePosition(videoId: string, t: number, duration: number): void {
  const pos = load<Positions>("pos", {}, "pos");
  // Only worth remembering past the intro and before the credits.
  if (t > 15 && (!duration || t < duration - 20)) pos[videoId] = Math.floor(t);
  else delete pos[videoId];
  const keys = Object.keys(pos);
  if (keys.length > 60) delete pos[keys[0]!];
  save("pos", pos);
}
