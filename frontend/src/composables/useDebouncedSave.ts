import { ref } from 'vue'

export function useDebouncedSave<T>(saver: (payload: T) => Promise<void>, delay = 1000) {
  const saving = ref(false)
  const savedAt = ref<Date | null>(null)
  let timer: ReturnType<typeof setTimeout> | null = null
  let pendingPayload: T | null = null

  async function flush() {
    if (!pendingPayload) return
    const payload = pendingPayload
    pendingPayload = null
    saving.value = true
    try {
      await saver(payload)
      savedAt.value = new Date()
    } finally {
      saving.value = false
    }
  }

  function schedule(payload: T) {
    pendingPayload = payload
    if (timer) clearTimeout(timer)
    timer = setTimeout(flush, delay)
  }

  return { saving, savedAt, schedule, flush }
}
