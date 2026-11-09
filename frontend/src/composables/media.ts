import { onBeforeUnmount, ref } from "vue";

export function useMediaQuery(query: string) {
  const mq = matchMedia(query);
  const matches = ref(mq.matches);
  const on = (e: MediaQueryListEvent) => (matches.value = e.matches);
  mq.addEventListener("change", on);
  onBeforeUnmount(() => mq.removeEventListener("change", on));
  return matches;
}
