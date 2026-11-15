import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setupGuards } from './router/guards'
import { setAuthBridge } from './api/client'
import { useAuthStore } from './stores/auth'
import { useBadgeStore } from './stores/badge'

import './styles/tokens.css'
import './styles/reset.css'
import './styles/global.css'
import './styles/responsive.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const auth = useAuthStore()

// 请求层与认证解耦：这里注入 token 读取、刷新与登出回调，避免循环依赖
setAuthBridge({
  getToken: () => auth.accessToken || null,
  refresh: () => auth.refresh(),
  onLost: () => {
    auth.clear()
    const current = router.currentRoute.value
    if (current.name !== 'login') {
      router.replace({ name: 'login', query: { redirect: current.fullPath } })
    }
  },
})

setupGuards(router)

app.mount('#app')

// 登录态下预热红点（不阻塞首屏）
if (auth.accessToken) {
  void useBadgeStore().refresh(true)
}
