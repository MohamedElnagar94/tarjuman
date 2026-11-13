import { ref } from "vue";
import { api, type UpdateState } from "@/api/client";

// One shared view of updates: the header shows "update available" and Settings -> Updates the details.
// The server asks GitHub at most every few hours, so reading this when the app opens costs nothing.
const state = ref<UpdateState | null>(null);
let loading: Promise<void> | null = null;

async function refresh(force = false): Promise<void> {
  try {
    state.value = await api.update(force);
  } catch {
    // A phone (updates are managed on the computer), or an older server without updates.
  }
}

export function useUpdates() {
  if (!loading) loading = refresh();
  return { state, refresh };
}
