<script setup lang="ts">
import { computed } from "vue";
import { RouterView } from "vue-router";
import { PhDeviceMobile } from "@phosphor-icons/vue";
import { useHealth } from "@/composables/health";
import AppHeader from "@/components/AppHeader.vue";
import BottomNav from "@/components/BottomNav.vue";
import ToastHost from "@/components/ToastHost.vue";

// Another device on the Wi-Fi that hasn't been paired gets this page instead of a wall of errors.
const { health } = useHealth();
const unpaired = computed(() => health.value?.paired === false);
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
