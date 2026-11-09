import { reactive } from "vue";

export interface Toast {
  id: number;
  text: string;
  tone: "info" | "ok" | "danger";
  action?: { label: string; run: () => void };
}

const state = reactive({ items: [] as Toast[] });
let seq = 0;

/** Short, transient messages. Anything the user must act on belongs inline, not here. */
export function toast(text: string, opts: { tone?: Toast["tone"]; action?: Toast["action"]; ms?: number } = {}): void {
  const t: Toast = { id: ++seq, text, tone: opts.tone || "info", action: opts.action };
  state.items.push(t);
  if (state.items.length > 3) state.items.shift();
  setTimeout(() => dismiss(t.id), opts.ms ?? (opts.action ? 7000 : 3200));
}

export function dismiss(id: number): void {
  const i = state.items.findIndex((x) => x.id === id);
  if (i >= 0) state.items.splice(i, 1);
}

export const toasts = state;
