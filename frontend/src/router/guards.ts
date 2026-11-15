import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/**
 * 登录守卫：
 * - auth 页无 access 时先用 refresh 静默续期，避免刷新页面即被踢；
 * - guest 页已登录直接回首页；
 * - 同步 document.title。
 */
export function setupGuards(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    document.title = to.meta.title ? `${to.meta.title} · 宿舍服务平台` : '宿舍服务平台'

    if (to.meta.auth && !auth.accessToken) {
      const ok = await auth.tryRefresh()
      if (ok) return true
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (to.meta.guest && auth.accessToken) return { name: 'home' }
    if (to.meta.leaderOnly && !auth.isLeader) return { name: 'home' }
    return true
  })

  router.afterEach((to) => {
    if (to.name === 'not-found') document.title = '页面不存在 · 宿舍服务平台'
  })
}
