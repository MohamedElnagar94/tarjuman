<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";
import { NAV } from "./nav";

const route = useRoute();
const isActive = (name: string) => route.name === name || (name === "home" && route.name === "watch");
</script>

<template>
  <nav class="bottom" :aria-label="$t('nav.aria')">
    <RouterLink v-for="n in NAV" :key="n.name" :to="n.to" class="tab" :class="{ on: isActive(n.name) }" :aria-current="isActive(n.name) ? 'page' : undefined">
      <component :is="n.icon" :size="22" :weight="isActive(n.name) ? 'fill' : 'regular'" />
      <span>{{ $t(n.label) }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.bottom {
  display: none;
}
@media (max-width: 759px) {
  .bottom {
    position: fixed;
    inset-inline: 0;
    bottom: 0;
    z-index: var(--z-nav);
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    height: calc(var(--bottom-nav-h) + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background: color-mix(in srgb, var(--bg) 92%, transparent);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-top: 1px solid var(--line);
  }
  .tab {
    display: grid;
    place-items: center;
    align-content: center;
    gap: 2px;
    color: var(--text-3);
    text-decoration: none;
    font-size: 11.5px;
    font-weight: 500;
  }
  .tab.on {
    color: var(--accent-ink);
  }
}
</style>
