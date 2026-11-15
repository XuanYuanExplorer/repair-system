import { onUnmounted, ref } from 'vue'

interface Options {
  interval?: number
  /** 最大轮询次数，超过后停止（0 = 不限） */
  max?: number
  /** 页面隐藏时暂停，恢复可见立即查一次 */
  pauseOnHidden?: boolean
}

/**
 * 支付结果 / 聊天增量轮询：可见性感知 + 卸载自动销毁。
 * fn 返回 true 表示已到终态，自动停止。
 */
export function usePolling(fn: () => Promise<boolean | void>, opts: Options = {}) {
  const { interval = 2000, max = 0, pauseOnHidden = true } = opts
  const running = ref(false)
  const count = ref(0)
  let timer: number | undefined

  function stop() {
    if (timer) window.clearInterval(timer)
    timer = undefined
    running.value = false
  }

  async function tick() {
    if (document.hidden && pauseOnHidden) return
    if (max && count.value >= max) {
      stop()
      return
    }
    count.value += 1
    try {
      const done = await fn()
      if (done) stop()
    } catch {
      // 轮询失败不打断，等下一轮
    }
  }

  function start() {
    stop()
    running.value = true
    void tick()
    timer = window.setInterval(() => void tick(), interval)
  }

  function onVisible() {
    if (!document.hidden && running.value) void tick()
  }

  document.addEventListener('visibilitychange', onVisible)
  onUnmounted(() => {
    stop()
    document.removeEventListener('visibilitychange', onVisible)
  })

  return { running, count, start, stop }
}
