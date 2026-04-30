<template>
  <div class="garden-page">
    <iframe
      ref="frameRef"
      class="garden-frame"
      :src="gardenUrl"
      title="赏花"
      @load="postAuthToGarden"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const frameRef = ref<HTMLIFrameElement | null>(null)

const gardenUrl = computed(() => import.meta.env.VITE_BOWER_URL || 'http://127.0.0.1:3000/')
const gardenOrigin = computed(() => {
  try {
    return new URL(gardenUrl.value, window.location.origin).origin
  } catch {
    return '*'
  }
})

function postAuthToGarden() {
  const target = frameRef.value?.contentWindow
  if (!target || !auth.accessToken) return

  target.postMessage({
    type: 'vidplan-auth',
    accessToken: auth.accessToken,
  }, gardenOrigin.value)
}

function onGardenMessage(event: MessageEvent) {
  if (gardenOrigin.value !== '*' && event.origin !== gardenOrigin.value) return
  if (event.data?.type === 'bower-ready') postAuthToGarden()
}

onMounted(() => {
  window.addEventListener('message', onGardenMessage)
  window.setTimeout(postAuthToGarden, 300)
})

onBeforeUnmount(() => {
  window.removeEventListener('message', onGardenMessage)
})
</script>

<style scoped>
.garden-page {
  height: calc(100vh - var(--vp-topbar-h));
  min-height: 520px;
  padding: 0;
  overflow: hidden;
}

.garden-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff8f0;
}
</style>
