<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { PhMoon, PhSun, PhArrowRight, PhArrowLeft } from "@phosphor-icons/vue";
import BrandMark from "./BrandMark.vue";
import ServerDot from "./ServerDot.vue";
import { NAV } from "./nav";
import { useUpdates } from "@/composables/updates";
import { useAppearance } from "@/composables/appearance";
import { useIntake } from "@/composables/intake";
import { usePrefs } from "@/composables/prefs";

const route = useRoute();
const prefs = usePrefs();
const { theme, toggleTheme, toggleLang } = useAppearance();
const { openLink, intake } = useIntake();

const quick = ref("");
const showQuick = computed(() => route.name !== "home");
const isActive = (name: string) => route.name === name || (name === "home" && route.name === "watch");

async function submitQuick() {
  if (await openLink(quick.value)) quick.value = "";
}
const { state: update } = useUpdates();
</script>

<template>
  <header class="bar">
    <div class="bar__in">
      <RouterLink to="/" class="brand" :aria-label="$t('nav.homeAria')">
        <BrandMark :size="32" />
        <span class="brand__name">{{ $t("app.name") }}</span>
      </RouterLink>

      <nav class="nav" :aria-label="$t('nav.aria')">
        <RouterLink v-for="n in NAV" :key="n.name" :to="n.to" class="nav__link" :class="{ on: isActive(n.name) }" :aria-current="isActive(n.name) ? 'page' : undefined">
          {{ $t(n.label) }}
        </RouterLink>
      </nav>

      <form v-if="showQuick" class="quick" role="search" @submit.prevent="submitQuick">
        <label class="sr-only" for="quick-link">{{ $t("intake.quickLabel") }}</label>
        <input id="quick-link" v-model="quick" class="input ltr" type="url" inputmode="url" autocomplete="off" spellcheck="false" :placeholder="$t('intake.quickPlaceholder')" :disabled="intake.busy" />
        <button class="btn btn--icon btn--sm btn--outline" type="submit" :aria-label="$t('intake.open')" :disabled="intake.busy">
          <PhArrowLeft v-if="prefs.uiLang === 'ar'" :size="16" />
          <PhArrowRight v-else :size="16" />
        </button>
      </form>

      <div class="tools">
        <RouterLink v-if="update?.available" to="/settings#updates" class="upd">{{ $t("updates.badge", { v: update.latest }) }}</RouterLink>
        <ServerDot />
        <button class="btn btn--quiet btn--sm lang" type="button" :aria-label="$t('appearance.switchLang')" @click="toggleLang">
          <span :lang="prefs.uiLang === 'ar' ? 'en' : 'ar'">{{ prefs.uiLang === "ar" ? "EN" : "ع" }}</span>
        </button>
        <button class="btn btn--quiet btn--icon btn--sm" type="button" :aria-label="theme === 'dark' ? $t('appearance.toLight') : $t('appearance.toDark')" @click="toggleTheme">
          <PhSun v-if="theme === 'dark'" :size="18" />
          <PhMoon v-else :size="18" />
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.upd {
  padding: 4px 10px;
  border-radius: var(--r-pill);
  background: var(--accent);
  color: var(--on-accent);
  font-size: var(--fs-xs);
  font-weight: 600;
  white-space: nowrap;
  text-decoration: none;
}
.bar {
  position: sticky;
  top: 0;
  z-index: var(--z-nav);
  height: var(--header-h);
  background: color-mix(in srgb, var(--bg) 86%, transparent);
  backdrop-filter: saturate(140%) blur(12px);
  -webkit-backdrop-filter: saturate(140%) blur(12px);
  border-bottom: 1px solid var(--line);
}
.bar__in {
  height: 100%;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 var(--s-6);
  display: flex;
  align-items: center;
  gap: var(--s-6);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex: none;
  border-radius: var(--r-sm);
}
.brand__name {
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 600;
  line-height: 1;
  padding-top: 2px;
}
.nav {
  display: flex;
  align-items: center;
  gap: 2px;
}
.nav__link {
  position: relative;
  padding: 8px 12px;
  border-radius: var(--r-sm);
  color: var(--text-2);
  text-decoration: none;
  font-size: var(--fs-sm);
  font-weight: 500;
  transition: color var(--dur) var(--ease), background var(--dur) var(--ease);
}
.nav__link:hover {
  color: var(--text);
  background: var(--surface-1);
}
.nav__link.on {
  color: var(--text);
}
.nav__link.on::after {
  content: "";
  position: absolute;
  inset-inline: 12px;
  bottom: -13px;
  height: 2px;
  border-radius: 2px;
  background: var(--accent-strong);
}
.quick {
  flex: 1;
  max-width: 420px;
  display: flex;
  gap: 6px;
  margin-inline-start: auto;
}
.quick .input {
  min-height: 34px;
  font-size: var(--fs-xs);
  background: var(--surface-1);
}
.tools {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-inline-start: auto;
}
.quick + .tools {
  margin-inline-start: 0;
}
.lang {
  min-width: 38px;
  font-weight: 600;
}
@media (max-width: 1080px) {
  .quick {
    display: none;
  }
}
@media (max-width: 759px) {
  .bar__in {
    padding: 0 var(--s-4);
    gap: var(--s-3);
  }
  .nav {
    display: none;
  }
  .brand__name {
    font-size: 21px;
  }
}
</style>
