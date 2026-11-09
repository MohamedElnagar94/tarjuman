<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <div class="page nf">
    <h1 class="page__title">{{ $t("missing.title") }}</h1>
    <p class="muted">{{ $t("missing.body") }}</p>
    <RouterLink to="/" class="btn btn--primary">{{ $t("missing.home") }}</RouterLink>
  </div>
</template>

<style scoped>
.nf {
  display: grid;
  justify-items: start;
  gap: var(--s-4);
  padding-top: var(--s-12);
}
</style>
