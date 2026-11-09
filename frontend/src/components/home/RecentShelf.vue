<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import { PhFilmStrip, PhPlay, PhX } from "@phosphor-icons/vue";
import { api } from "@/api/client";
import type { MediaItem } from "@/api/types";
import { getPosition, useRecent } from "@/composables/recent";
import { thumbnailFor } from "@/lib/links";
import { formatTime } from "@/lib/time";

const { t } = useI18n();
const { recent, forget } = useRecent();
const media = ref<MediaItem[]>([]);
const broken = ref(new Set<string>());

onMounted(async () => {
  try {
    media.value = (await api.media()).items || [];
  } catch {
    media.value = [];
  }
});

interface Card {
  id: string;
  title: string;
  url: string;
  thumb: string | null;
  progress: number;
  meta: string;
  recent: boolean;
}

const cards = computed<Card[]>(() => {
  const seen = new Set<string>();
  const out: Card[] = [];
  for (const r of recent.value) {
    seen.add(r.videoId);
    const at = getPosition(r.videoId) || 0;
    out.push({
      id: r.videoId,
      title: r.title || r.videoId,
      url: r.url,
      thumb: thumbnailFor(r.videoId),
      progress: r.lengthSeconds && at ? Math.min(1, at / r.lengthSeconds) : 0,
      meta: at ? t("home.recent.at", { time: formatTime(at) }) : r.lengthSeconds ? formatTime(r.lengthSeconds) : "",
      recent: true,
    });
  }
  for (const m of media.value) {
    const id = "media:" + m.id;
    if (seen.has(id) || m.link && seen.has(m.link)) continue;
    out.push({ id, title: m.title, url: m.link, thumb: null, progress: 0, meta: m.transcribed ? t("home.recent.transcribed") : t("home.recent.onDevice"), recent: false });
  }
  return out.slice(0, 8);
});
</script>

<template>
  <section class="shelf" aria-labelledby="shelf-title">
    <div class="shelf__head">
      <h2 id="shelf-title" class="section-title">{{ $t("home.recent.title") }}</h2>
      <RouterLink v-if="media.length" to="/library#media" class="more">{{ $t("home.recent.allMedia") }}</RouterLink>
    </div>

    <div v-if="!cards.length" class="empty">
      <strong>{{ $t("home.recent.emptyTitle") }}</strong>
      <span>{{ $t("home.recent.emptyBody") }}</span>
    </div>

    <ul v-else class="grid">
      <li v-for="c in cards" :key="c.id" class="card">
        <RouterLink :to="{ name: 'watch', query: { url: c.url } }" class="card__link">
          <div class="thumb">
            <img v-if="c.thumb && !broken.has(c.id)" :src="c.thumb" alt="" loading="lazy" decoding="async" @error="broken.add(c.id)" />
            <div v-else class="thumb__ph"><PhFilmStrip :size="28" /></div>
            <span class="play" aria-hidden="true"><PhPlay :size="16" weight="fill" /></span>
            <span v-if="c.progress" class="bar" :style="{ '--p': c.progress }"></span>
          </div>
          <span class="title" dir="auto">{{ c.title }}</span>
          <span v-if="c.meta" class="meta">{{ c.meta }}</span>
        </RouterLink>
        <button v-if="c.recent" type="button" class="x btn btn--icon btn--sm" :aria-label="$t('home.recent.forget', { title: c.title })" @click="forget(c.id)">
          <PhX :size="14" />
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.shelf__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s-4);
  margin-bottom: var(--s-4);
}
.more {
  color: var(--accent-ink);
  font-size: var(--fs-sm);
  text-underline-offset: 3px;
}
.grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--s-5) var(--s-4);
}
.card {
  position: relative;
  min-width: 0;
}
.card__link {
  display: grid;
  gap: 6px;
  text-decoration: none;
  border-radius: var(--r-md);
}
.thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: var(--r-md);
  overflow: hidden;
  background: var(--surface-2);
  border: 1px solid var(--line);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms var(--ease);
}
.card__link:hover img {
  transform: scale(1.03);
}
.thumb__ph {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.75);
  background:
    repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.06) 0 1px, transparent 1px 18px),
    linear-gradient(160deg, var(--lapis-500), var(--lapis-900));
}
.play {
  position: absolute;
  bottom: 10px;
  inset-inline-end: 10px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--on-accent);
  opacity: 0;
  transform: translateY(4px);
  transition: opacity var(--dur) var(--ease), transform var(--dur) var(--ease);
}
.card__link:hover .play,
.card__link:focus-visible .play {
  opacity: 1;
  transform: none;
}
.bar {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  height: 3px;
  background: rgba(0, 0, 0, 0.4);
}
.bar::after {
  content: "";
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: calc(var(--p) * 100%);
  background: var(--accent-strong);
}
.title {
  font-size: var(--fs-sm);
  font-weight: 500;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.meta {
  font-size: var(--fs-xs);
  color: var(--text-2);
}
.x {
  position: absolute;
  top: 8px;
  inset-inline-start: 8px;
  --btn-bg: rgba(5, 7, 26, 0.6);
  --btn-fg: #fff;
  opacity: 0;
}
.card:hover .x,
.x:focus-visible {
  opacity: 1;
}
@media (hover: none) {
  .x {
    opacity: 1;
  }
}
@media (max-width: 560px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--s-4) var(--s-3);
  }
}
</style>
