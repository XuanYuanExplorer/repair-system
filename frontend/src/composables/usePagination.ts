import { ref } from 'vue'

/** 触底加载：配合 page / has_more 列表接口，loading 时忽略重复触发。 */
export function usePagination<T>(fetcher: (page: number) => Promise<{ items: T[]; has_more: boolean }>) {
  const list = ref<T[]>([]) as { value: T[] }
  const page = ref(1)
  const loading = ref(false)
  const finished = ref(false)
  const error = ref('')

  async function load(reset = false) {
    if (loading.value) return
    if (finished.value && !reset) return
    if (reset) {
      page.value = 1
      finished.value = false
      list.value = []
    }
    loading.value = true
    error.value = ''
    try {
      const res = await fetcher(page.value)
      list.value = reset ? res.items : [...list.value, ...res.items]
      finished.value = !res.has_more
      page.value += 1
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return { list, page, loading, finished, error, load }
}
