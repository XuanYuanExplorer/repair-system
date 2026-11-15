import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { messageApi } from '@/api/message'
import { useAuthStore } from '@/stores/auth'
import { paymentApi } from '@/api/payment'
import type { HomeSummary } from '@/api/types'

const STALE_MS = 60_000

/** 导航红点与首页双格数字的唯一来源：60s 内复用缓存，避免每个页面都打接口。 */
export const useBadgeStore = defineStore('badge', () => {
  const unreadTotal = ref(0)
  const dueCount = ref(0)
  const dueAmount = ref('0.00')
  const activeOrders = ref(0)
  const updatedAt = ref(0)

  const hasUnread = computed(() => unreadTotal.value > 0)

  /** 首页聚合数据到达时顺带刷新，不额外发请求。 */
  function fromSummary(s: HomeSummary) {
    unreadTotal.value = s.unread?.total ?? 0
    dueCount.value = s.due?.count ?? 0
    dueAmount.value = s.due?.amount ?? '0.00'
    activeOrders.value = s.orders?.active_count ?? 0
    updatedAt.value = Date.now()
  }

  async function refresh(force = false) {
    if (!useAuthStore().accessToken) return
    if (!force && Date.now() - updatedAt.value < STALE_MS) return
    try {
      const [unread, summary] = await Promise.all([messageApi.unreadCount(), paymentApi.summary()])
      unreadTotal.value = unread.total
      dueCount.value = summary.unpaid_count + summary.overdue_count
      dueAmount.value = summary.due_amount
      updatedAt.value = Date.now()
    } catch {
      // 红点失败静默：不影响主流程
    }
  }

  function decUnread(n = 1) {
    unreadTotal.value = Math.max(0, unreadTotal.value - n)
  }

  function clearUnread() {
    unreadTotal.value = 0
  }

  return { unreadTotal, dueCount, dueAmount, activeOrders, updatedAt, hasUnread, fromSummary, refresh, decUnread, clearUnread }
})
