/* Voice packs (Settings -> Voice packs), shared by the settings page and the export panel. */
import { ref } from "vue";
import { api } from "@/api/client";
import type { PacksState } from "@/api/types";

const state = ref<PacksState | null>(null);
let loading: Promise<void> | null = null;

export function usePacks() {
  if (!state.value && !loading) {
    loading = api
      .packs()
      .then((s) => void (state.value = s))
      .catch(() => {})
      .finally(() => (loading = null));
  }
  return { packs: state, refresh: async () => void (state.value = await api.packs()) };
}

export const HABIBI_DIALECTS = ["EGY", "IRQ", "MAR", "ALG", "MSA"] as const;
