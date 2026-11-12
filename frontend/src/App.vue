<script setup lang="ts">
import { computed, onMounted } from "vue";
import { RouterView } from "vue-router";
import { PhDeviceMobile } from "@phosphor-icons/vue";
import { useHealth } from "@/composables/health";
import AppHeader from "@/components/AppHeader.vue";
import BottomNav from "@/components/BottomNav.vue";
import ToastHost from "@/components/ToastHost.vue";
import { api } from "@/api/client";

// Another device on the Wi-Fi that hasn't been paired gets this page instead of a wall of errors.
const { health } = useHealth();
const unpaired = computed(() => health.value?.paired === false);

// In the desktop app the window is a browser profile of its own: a link to another site would open
// there, away from the user's browser (and its extensions). Send such links to the default browser.
onMounted(async () => {
  try {
    if (!(await api.desktop()).available) return;
  } catch {
    return; // a phone, or a server without the desktop app
  }
  document.addEventListener(
    "click",
    (e) => {
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target !== "_blank" || a.origin === location.origin || !/^https?:$/.test(a.protocol)) return;
      e.preventDefault();
      api.openExternal(a.href).catch(() => window.open(a.href, "_blank", "noopener"));
    },
    true,
  );
});
</script>

<template>
  <a class="skip" href="#main">{{ $t("a11y.skip") }}</a>
  <AppHeader />
  <main id="main" tabindex="-1">
    <section v-if="unpaired" class="pairing">
      <PhDeviceMobile :size="44" class="pairing__icon" />
      <h1>{{ $t("phone.unpairedTitle") }}</h1>
      <p>{{ $t("phone.unpairedBody") }}</p>
      <ol>
        <li>{{ $t("phone.unpaired1") }}</li>
        <li>{{ $t("phone.unpaired2") }}</li>
      </ol>
    </section>
    <RouterView v-else />
  </main>
  <BottomNav />
  <ToastHost />
</template>

<style scoped>
.skip {
  position: fixed;
  top: 8px;
  inset-inline-start: 8px;
  z-index: var(--z-toast);
  padding: 8px 14px;
  border-radius: var(--r-sm);
  background: var(--accent);
  color: var(--on-accent);
  font-weight: 600;
  transform: translateY(-200%);
}
.skip:focus {
  transform: none;
}
main:focus {
  outline: none;
}
.pairing {
  max-width: 34rem;
  margin: 12vh auto;
  padding: 0 var(--s-5);
  line-height: 1.85;
}
.pairing h1 {
  font-size: var(--fs-xl);
  margin: var(--s-3) 0;
}
.pairing__icon {
  color: var(--accent);
}
.pairing ol {
  padding-inline-start: 1.2em;
}
</style>
