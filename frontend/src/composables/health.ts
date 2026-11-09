import { ref } from "vue";
import { api } from "@/api/client";
import type { Health } from "@/api/types";

const health = ref<Health | null>(null);
/** "unknown" until the first answer, "down" when the local server does not answer. */
const status = ref<"unknown" | "up" | "down">("unknown");
let timer: number | undefined;

async function refresh(): Promise<void> {
  try {
    health.value = await api.health();
    status.value = "up";
  } catch {
    status.value = "down";
  }
}

export function useHealth() {
  if (timer === undefined) {
    void refresh();
    timer = window.setInterval(refresh, 30000);
  }
  return { health, status, refresh };
}
