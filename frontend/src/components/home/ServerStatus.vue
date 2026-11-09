<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhArrowClockwise } from "@phosphor-icons/vue";
import CopyCommand from "@/components/CopyCommand.vue";
import { useHealth } from "@/composables/health";

const { t } = useI18n();
const { health, status, refresh } = useHealth();

interface Row {
  key: string;
  ok: boolean | null;
  title: string;
  detail: string;
  cmd?: string;
  link?: { to: string; label: string };
}

const SETUP = "python -m tarjuman setup";

const rows = computed<Row[]>(() => {
  const h = health.value;
  if (!h) return [];
  const tts = h.tts || ({} as typeof h.tts);
  return [
    {
      key: "translate",
      ok: !h.providers?.googleCooling,
      title: t("status.translate.title"),
      detail: h.providers?.googleCooling ? t("status.translate.cooling") : t("status.translate.ok"),
    },
    {
      key: "whisper",
      ok: !!h.whisper?.installed,
      title: t("status.whisper.title"),
      detail: h.whisper?.installed ? t("status.whisper.ok", { model: h.whisper.model || "base" }) : t("status.whisper.missing"),
      cmd: h.whisper?.installed ? undefined : SETUP,
    },
    {
      key: "voices",
      ok: !!tts.installed,
      title: t("status.voices.title"),
      detail: tts.installed ? t("status.voices.ok") : t("status.voices.missing"),
      cmd: tts.installed ? undefined : SETUP,
    },
    {
      key: "ffmpeg",
      ok: !!h.ffmpeg,
      title: t("status.ffmpeg.title"),
      detail: h.ffmpeg ? t("status.ffmpeg.ok") : t("status.ffmpeg.missing"),
      cmd: h.ffmpeg ? undefined : SETUP,
    },
    {
      key: "ai",
      ok: h.ai?.ready ? true : null,
      title: t("status.ai.title"),
      detail: h.ai?.ready ? t("status.ai.ok", { model: h.ai.model }) : t("status.ai.off"),
      link: { to: "/settings#ai", label: h.ai?.ready ? t("status.ai.change") : t("status.ai.setup") },
    },
  ];
});
</script>

<template>
  <section id="status" class="status panel" aria-labelledby="status-title">
    <header class="head">
      <h2 id="status-title" class="panel__title">{{ $t("status.title") }}</h2>
      <button class="btn btn--quiet btn--icon btn--sm" type="button" :aria-label="$t('status.recheck')" @click="refresh"><PhArrowClockwise :size="16" /></button>
    </header>

    <div v-if="status === 'down'" class="notice notice--danger">
      <div class="notice__body">
        <strong>{{ $t("status.down.title") }}</strong>
        <span>{{ $t("status.down.body") }}</span>
        <CopyCommand cmd="python -m tarjuman" />
      </div>
    </div>

    <div v-else-if="!health" class="rows" aria-busy="true">
      <div v-for="n in 4" :key="n" class="skeleton sk"></div>
    </div>

    <template v-else>
      <p class="panel__lead">{{ $t("status.up", { port: health.port, version: health.version }) }}</p>
      <ul class="rows">
        <li v-for="r in rows" :key="r.key" class="row">
          <span class="state" :class="r.ok === true ? 'ok' : r.ok === false ? 'bad' : 'idle'" aria-hidden="true"></span>
          <div class="txt">
            <strong>{{ r.title }}</strong>
            <span>{{ r.detail }}</span>
            <CopyCommand v-if="r.cmd" :cmd="r.cmd" />
            <RouterLink v-if="r.link" :to="r.link.to" class="lnk">{{ r.link.label }}</RouterLink>
          </div>
          <span class="sr-only">{{ r.ok === true ? $t("status.ready") : r.ok === false ? $t("status.notReady") : $t("status.optional") }}</span>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.rows {
  list-style: none;
  margin: var(--s-4) 0 0;
  padding: 0;
  display: grid;
  gap: 2px;
}
.sk {
  height: 44px;
}
.row {
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: var(--s-3);
  padding: var(--s-3) 0;
  border-top: 1px solid var(--line);
}
.row:first-child {
  border-top: 0;
}
.state {
  width: 9px;
  height: 9px;
  margin-top: 7px;
  transform: rotate(45deg);
  border-radius: 2px;
  background: var(--text-3);
}
.state.ok {
  background: var(--ok);
}
.state.bad {
  background: var(--accent-strong);
}
.txt {
  display: grid;
  gap: 4px;
  font-size: var(--fs-sm);
  min-width: 0;
}
.txt span {
  color: var(--text-2);
}
.txt strong {
  font-weight: 600;
}
.lnk {
  color: var(--accent-ink);
  font-size: var(--fs-sm);
  font-weight: 500;
  text-underline-offset: 3px;
  justify-self: start;
}
.notice {
  margin-top: var(--s-4);
}
</style>
