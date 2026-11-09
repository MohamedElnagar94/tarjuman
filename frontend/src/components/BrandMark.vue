<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 34 });
</script>

<template>
  <img class="mark" src="/favicon.svg" :width="size" :height="size" alt="" />
</template>

<style scoped>
.mark {
  flex: none;
  border-radius: 24%;
}
</style>
