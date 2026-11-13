<script setup lang="ts">
import { subtitleFont } from "@/lib/fonts";
import { computed } from "vue";
import { tokenize } from "@/lib/words";

const props = defineProps<{
  src: string;
  text: string;
  /** Translation not ready yet: the source line is shown, dimmed. */
  pending?: boolean;
  bilingual: boolean;
  position: "top" | "bottom";
  size: number;
  bgo: number;
  quiz?: boolean;
  hidden?: boolean;
  rtl: boolean;
  /** Font id (lib/fonts.ts); the default font when missing. */
  font?: string;
  /** Scales with the player width. */
  scale?: number;
  /** Static placement for previews (no absolute positioning). */
  inline?: boolean;
}>();
const emit = defineEmits<{ word: [word: string, el: Element] }>();

const tokens = computed(() => (props.bilingual && props.src ? tokenize(props.src) : []));
const main = computed(() => props.text || props.src || "");
const fontStyle = computed(() => {
  const f = subtitleFont(props.font);
  return { "--sub-font": f.family, "--sub-weight": String(f.weight) };
});
</script>

<template>
  <div
    class="subs"
    :class="[position, { off: hidden || !main, quiz, inline }]"
    :style="{ '--sub-size': size + 'px', '--bgo': String(bgo), '--scale': String(scale ?? 1), ...fontStyle }"
    aria-live="off"
  >
    <div v-if="tokens.length" class="line en" dir="ltr" lang="en">
      <span>
        <template v-for="(tk, k) in tokens" :key="k">
          <button v-if="tk.word" type="button" class="w" @click.stop="emit('word', tk.lookup, $event.currentTarget as Element)">{{ tk.text }}</button>
          <template v-else>{{ tk.text }}</template>
        </template>
      </span>
    </div>
    <div v-if="main" class="line tr" :class="{ pending }" :dir="pending ? 'ltr' : rtl ? 'rtl' : 'ltr'">
      <span>{{ main }}</span>
    </div>
  </div>
</template>

<style scoped>
.subs {
  position: absolute;
  inset-inline: 5%;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  pointer-events: none;
  font-size: calc(var(--sub-size) * var(--scale));
  transition: opacity 150ms var(--ease);
}
.subs.bottom {
  bottom: 12%;
}
.subs.top {
  top: 7%;
}
.subs.inline {
  position: static;
}
.subs.off {
  opacity: 0;
}
.line {
  margin: 0.08em 0;
  max-width: 100%;
}
.line span {
  background: rgba(5, 7, 26, var(--bgo));
  color: #fff;
  line-height: 1.6;
  padding: 0.06em 0.45em;
  border-radius: 0.28em;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
  -webkit-box-decoration-break: clone;
  box-decoration-break: clone;
}
.tr {
  font-family: var(--sub-font, var(--font-ui));
  font-weight: var(--sub-weight, 600);
}
.tr.pending span {
  color: #cfd3ea;
  font-weight: 400;
}
.en {
  font-size: 0.64em;
  font-weight: 400;
  pointer-events: auto;
}
.w {
  display: inline;
  padding: 0;
  margin: 0;
  border: 0;
  background: none;
  color: inherit;
  font: inherit;
  text-shadow: inherit;
  border-radius: 3px;
  cursor: pointer;
}
.w:hover,
.w:focus-visible {
  background: rgba(255, 210, 122, 0.32);
  outline: none;
}
.quiz {
  pointer-events: auto;
}
.quiz .tr span {
  filter: blur(7px);
  transition: filter 150ms var(--ease);
}
.quiz:hover .tr span,
.quiz:focus-within .tr span {
  filter: none;
}
</style>
