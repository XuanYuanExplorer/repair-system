import { onMounted, ref, type Ref } from 'vue'
import { errText } from '@/api/client'

interface Options {
  /** 挂载后立即请求，默认 true */
  immediate?: boolean
  /** 内存缓存时长（ms），同页重复进入可先用旧数据渲染 */
  cacheMs?: number
}

let cacheStore = new Map<string, { at: number; data: unknown }>()

/**
 * 三态封装：loading / error / data + refresh，所有异步区块统一用它。
 * 组件卸载后不再写状态，避免 keep-alive 场景的串页。
 */
export function useAsyncData<T>(key: string, fetcher: () => Promise<T>, opts: Options = {}) {
  const { immediate = true, cacheMs = 0 } = opts
  const cached = cacheMs ? cacheStore.get(key) : undefined
  const data = ref<T | null>((cached?.data as T) ?? null) as Ref<T | null>
  const loading = ref(!cached)
  const error = ref('')
  let alive = true
  let lastAt = cached?.at ?? 0

  async function refresh(silent = false) {
    if (!silent) {
      error.value = ''
      if (!data.value) loading.value = true
    }
    try {
      const res = await fetcher()
      if (!alive) return
      data.value = res
      lastAt = Date.now()
      if (cacheMs) cacheStore.set(key, { at: lastAt, data: res })
    } catch (e) {
      if (!alive) return
      error.value = errText(e, '加载失败，请稍后重试')
    } finally {
      if (alive) loading.value = false
    }
  }

  /** 60s 内直接用缓存，超时才静默刷新（首页/列表页体验用）。 */
  function refreshIfStale(maxAge = 60_000) {
    if (!lastAt || Date.now() - lastAt > maxAge) return refresh(true)
    return Promise.resolve()
  }

  if (immediate) onMounted(() => refresh())

  return { data, loading, error, refresh, refreshIfStale, set: (v: T | null) => (data.value = v) }
}
