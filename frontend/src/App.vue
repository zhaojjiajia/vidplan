<template>
  <RoseBackdrop />
  <div class="app-content">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import RoseBackdrop from '@/components/RoseBackdrop.vue'
</script>

<style scoped>
.app-content {
  position: relative;
  z-index: 1;
  min-height: 100%;
}
</style>
