<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { PhLinkSimple, PhUploadSimple, PhWarningCircle, PhX } from "@phosphor-icons/vue";
import ProgressMeter from "@/components/ui/ProgressMeter.vue";
import { useIntake } from "@/composables/intake";

const { intake, openLink, upload, cancel } = useIntake();
const link = ref("");
const file = ref<HTMLInputElement | null>(null);
const input = ref<HTMLInputElement | null>(null);
const dragging = ref(false);
let depth = 0;

async function submit() {
  if (await openLink(link.value)) link.value = "";
}

function pick(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0];
  (e.target as HTMLInputElement).value = "";
  void upload(f);
}

/* A file can be dropped anywhere on the page. */
const hasFiles = (e: DragEvent) => [...(e.dataTransfer?.types || [])].includes("Files");
function onEnter(e: DragEvent) {
  if (!hasFiles(e)) return;
  depth++;
  dragging.value = true;
}
function onOver(e: DragEvent) {
  if (hasFiles(e)) e.preventDefault();
}
function onLeave() {
  depth = Math.max(0, depth - 1);
  if (!depth) dragging.value = false;
}
function onDrop(e: DragEvent) {
  depth = 0;
  dragging.value = false;
  const f = e.dataTransfer?.files?.[0];
  if (!f) return;
  e.preventDefault();
  void upload(f);
}

onMounted(() => {
  window.addEventListener("dragenter", onEnter);
  window.addEventListener("dragover", onOver);
  window.addEventListener("dragleave", onLeave);
  window.addEventListener("drop", onDrop);
  input.value?.focus({ preventScroll: true });
});
onBeforeUnmount(() => {
  window.removeEventListener("dragenter", onEnter);
  window.removeEventListener("dragover", onOver);
  window.removeEventListener("dragleave", onLeave);
  window.removeEventListener("drop", onDrop);
});
</script>

<template>
  <div class="intake">
    <form class="bar" :class="{ busy: intake.busy }" @submit.prevent="submit">
      <PhLinkSimple class="lead" :size="20" aria-hidden="true" />
      <label class="sr-only" for="link">{{ $t("intake.label") }}</label>
      <input
        id="link"
        ref="input"
        v-model="link"
        class="ltr"
        type="text"
        inputmode="url"
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        :placeholder="$t('intake.placeholder')"
        :disabled="intake.busy"
        :aria-invalid="!!intake.error"
        aria-describedby="intake-help intake-error"
      />
      <button class="btn btn--primary btn--lg" type="submit" :disabled="intake.busy">{{ $t("intake.open") }}</button>
    </form>

    <div class="below">
      <p id="intake-help" class="help">{{ $t("intake.help") }}</p>
      <button class="btn btn--outline btn--sm" type="button" :disabled="intake.busy" @click="file?.click()">
        <PhUploadSimple :size="16" />
        {{ $t("intake.upload") }}
      </button>
      <input ref="file" type="file" accept="video/*,audio/*,.mkv" hidden @change="pick" />
    </div>

    <div v-if="intake.busy" class="progress">
      <ProgressMeter :value="intake.progress" :label="intake.label" />
      <button class="btn btn--quiet btn--sm" type="button" @click="cancel"><PhX :size="14" />{{ $t("common.cancel") }}</button>
    </div>

    <p v-if="intake.error" id="intake-error" class="notice notice--danger" role="alert">
      <PhWarningCircle :size="18" />
      <span>{{ intake.error }}</span>
    </p>

    <Teleport to="body">
      <div v-if="dragging" class="drop" aria-hidden="true">
        <div class="drop__card">
          <PhUploadSimple :size="36" />
          <strong>{{ $t("intake.dropTitle") }}</strong>
          <span>{{ $t("intake.dropHint") }}</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.intake {
  display: grid;
  gap: var(--s-3);
}
.bar {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  padding: 6px;
  padding-inline-start: var(--s-4);
  border: 1px solid var(--line-2);
  border-radius: var(--r-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-1);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.bar:focus-within {
  border-color: var(--accent-line);
  box-shadow: 0 0 0 4px var(--accent-soft), var(--shadow-1);
}
.lead {
  color: var(--text-3);
  flex: none;
}
.bar input {
  flex: 1;
  min-width: 0;
  min-height: 48px;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 16px;
  text-align: left;
}
.bar input::placeholder {
  color: var(--text-3);
}
.below {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  flex-wrap: wrap;
}
.help {
  color: var(--text-2);
  font-size: var(--fs-xs);
}
.progress {
  display: flex;
  align-items: center;
  gap: var(--s-3);
}
.drop {
  position: fixed;
  inset: 0;
  z-index: var(--z-dialog);
  display: grid;
  place-items: center;
  background: var(--scrim);
  backdrop-filter: blur(3px);
  pointer-events: none;
}
.drop__card {
  display: grid;
  justify-items: center;
  gap: var(--s-2);
  padding: var(--s-10) var(--s-12);
  border: 2px dashed var(--accent);
  border-radius: var(--r-lg);
  background: var(--surface-1);
  color: var(--text);
  text-align: center;
}
.drop__card svg {
  color: var(--accent-ink);
}
.drop__card span {
  color: var(--text-2);
  font-size: var(--fs-sm);
}
@media (max-width: 560px) {
  .bar {
    flex-wrap: wrap;
    padding: var(--s-2);
  }
  .lead {
    display: none;
  }
  .bar input {
    flex-basis: 100%;
    padding: 0 var(--s-2);
  }
  .bar .btn {
    width: 100%;
  }
}
</style>
