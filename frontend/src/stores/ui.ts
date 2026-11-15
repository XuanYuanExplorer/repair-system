import { ref } from 'vue'
import { defineStore } from 'pinia'

export interface ToastItem {
  id: number
  text: string
  tone: 'ink' | 'red'
}

let seq = 0

/** 全局轻提示（单行、无图标、2.4s 自动消失，同时最多 2 条）。 */
export const useUiStore = defineStore('ui', () => {
  const toasts = ref<ToastItem[]>([])
  const pending = ref(0)

  function toast(text: string, tone: 'ink' | 'red' = 'ink') {
    if (!text) return
    const item: ToastItem = { id: ++seq, text, tone }
    toasts.value = [...toasts.value.slice(-1), item]
    window.setTimeout(() => dismiss(item.id), 2400)
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  function loading(on: boolean) {
    pending.value = Math.max(0, pending.value + (on ? 1 : -1))
  }

  return { toasts, pending, toast, dismiss, loading }
})
