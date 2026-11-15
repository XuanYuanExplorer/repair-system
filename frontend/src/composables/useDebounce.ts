import { ref, watch, type Ref } from 'vue'

/** 防抖值：搜索框 300ms 后才触发请求。 */
export function useDebouncedRef<T>(source: Ref<T>, delay = 300) {
  const debounced = ref(source.value) as Ref<T>
  let timer: number | undefined
  watch(source, (v) => {
    if (timer) window.clearTimeout(timer)
    timer = window.setTimeout(() => (debounced.value = v), delay)
  })
  return debounced
}

export function useDebounceFn<A extends unknown[]>(fn: (...args: A) => void, delay = 300) {
  let timer: number | undefined
  return (...args: A) => {
    if (timer) window.clearTimeout(timer)
    timer = window.setTimeout(() => fn(...args), delay)
  }
}
