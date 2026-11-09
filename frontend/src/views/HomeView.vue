<script setup lang="ts">
import { onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { PhBookOpenText, PhChatsCircle, PhDownloadSimple, PhMicrophoneStage, PhSubtitles } from "@phosphor-icons/vue";
import HeroPreview from "@/components/home/HeroPreview.vue";
import LinkIntake from "@/components/home/LinkIntake.vue";
import RecentShelf from "@/components/home/RecentShelf.vue";
import ServerStatus from "@/components/home/ServerStatus.vue";

const { t } = useI18n();
onMounted(() => (document.title = t("app.name") + " | " + t("app.tagline")));

const CAN = [
  { key: "subs", icon: PhSubtitles },
  { key: "dub", icon: PhMicrophoneStage },
  { key: "export", icon: PhDownloadSimple },
  { key: "ask", icon: PhChatsCircle },
  { key: "learn", icon: PhBookOpenText },
] as const;
</script>

<template>
  <div class="page home">
    <section class="hero">
      <div class="hero__copy">
        <h1 class="hero__title">{{ $t("home.title") }}</h1>
        <p class="hero__lead">{{ $t("home.lead") }}</p>
        <LinkIntake />
      </div>
      <HeroPreview class="hero__art" />
    </section>

    <RecentShelf class="block" />

    <div class="split block">
      <section class="can" aria-labelledby="can-title">
        <h2 id="can-title" class="section-title">{{ $t("home.can.title") }}</h2>
        <ol class="can__list">
          <li v-for="c in CAN" :key="c.key" class="can__item">
            <span class="can__icon"><component :is="c.icon" :size="22" /></span>
            <div>
              <h3>{{ $t(`home.can.${c.key}.title`) }}</h3>
              <p>{{ $t(`home.can.${c.key}.body`) }}</p>
            </div>
          </li>
        </ol>
      </section>
      <ServerStatus />
    </div>
  </div>
</template>

<style scoped>
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
  gap: var(--s-12);
  align-items: center;
  padding: var(--s-8) 0 var(--s-6);
}
.hero__copy {
  display: grid;
  gap: var(--s-5);
}
.hero__title {
  font-family: var(--font-display);
  font-size: var(--fs-3xl);
  font-weight: 700;
  line-height: 1.2;
}
:global([dir="ltr"]) .hero__title {
  letter-spacing: -0.01em;
}
.hero__lead {
  color: var(--text-2);
  font-size: var(--fs-lg);
  max-width: 46ch;
}
.block {
  margin-top: var(--s-12);
}
.split {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: var(--s-8);
  align-items: start;
}
.can__list {
  list-style: none;
  margin: var(--s-5) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s-6) var(--s-6);
}
.can__item {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: var(--s-3);
  align-items: start;
}
.can__item:first-child {
  grid-column: 1 / -1;
}
.can__icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--r-md);
  background: var(--lapis-soft);
  color: var(--lapis);
}
.can__item:first-child .can__icon {
  background: var(--accent-soft);
  color: var(--accent-ink);
}
.can__item h3 {
  font-size: var(--fs-md);
  font-weight: 600;
  margin-bottom: 2px;
}
.can__item p {
  color: var(--text-2);
  font-size: var(--fs-sm);
  max-width: 52ch;
}
@media (max-width: 1023px) {
  .hero {
    grid-template-columns: 1fr;
    gap: var(--s-8);
    padding-top: var(--s-4);
  }
  .hero__art {
    max-width: 640px;
  }
  .split {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 560px) {
  .can__list {
    grid-template-columns: 1fr;
  }
  .block {
    margin-top: var(--s-10);
  }
}
</style>
