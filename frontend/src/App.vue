<script setup lang="ts">
import { RouterView } from "vue-router";
import AppHeader from "@/components/AppHeader.vue";
import BottomNav from "@/components/BottomNav.vue";
import ToastHost from "@/components/ToastHost.vue";
</script>

<template>
  <a class="skip" href="#main">{{ $t("a11y.skip") }}</a>
  <AppHeader />
  <main id="main" tabindex="-1">
    <RouterView />
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
</style>
