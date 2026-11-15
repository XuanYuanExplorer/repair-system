import { computed, onUnmounted, ref } from 'vue'
import { fmtCountdown } from '@/utils/format'

/** 验证码 / 支付倒计时：卸载自动清理，支持外部校准（以服务端时间为准）。 */
export function useCountdown(initial = 0) {
  const left = ref(initial)
  let timer: number | undefined

  function stop() {
    if (timer) window.clearInterval(timer)
    timer = undefined
  }

  function start(seconds = left.value) {
    stop()
    left.value = Math.max(0, Math.floor(seconds))
    if (left.value <= 0) return
    timer = window.setInterval(() => {
      left.value -= 1
      if (left.value <= 0) stop()
    }, 1000)
  }

  function reset(seconds = 0) {
    stop()
    left.value = seconds
  }

  const text = computed(() => fmtCountdown(left.value))
  const active = computed(() => left.value > 0)

  onUnmounted(stop)

  return { left, text, active, start, stop, reset }
}
