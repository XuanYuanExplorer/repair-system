import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'
import type { LoginResult, SessionUser } from '@/api/types'

const K_ACCESS = 'ds.access'
const K_REFRESH = 'ds.refresh'
const K_USER = 'ds.user'

function readAccess(): string {
  return sessionStorage.getItem(K_ACCESS) || ''
}

function readRefresh(): string {
  // 勾选「记住登录」→ localStorage（7 天）；否则 sessionStorage（关闭浏览器失效）
  return localStorage.getItem(K_REFRESH) || sessionStorage.getItem(K_REFRESH) || ''
}

function writeRefresh(token: string, remember: boolean) {
  localStorage.removeItem(K_REFRESH)
  sessionStorage.removeItem(K_REFRESH)
  ;(remember ? localStorage : sessionStorage).setItem(K_REFRESH, token)
}

function readUser(): SessionUser | null {
  try {
    const raw = sessionStorage.getItem(K_USER)
    return raw ? (JSON.parse(raw) as SessionUser) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(readAccess())
  const refreshToken = ref(readRefresh())
  const user = ref<SessionUser | null>(readUser())

  const isLogged = computed(() => !!accessToken.value)
  const isLeader = computed(() => !!user.value?.is_leader)
  const displayName = computed(() => user.value?.name || '')
  const roomText = computed(() => user.value?.room || '')

  let refreshing: Promise<string | null> | null = null

  function setSession(res: LoginResult, remember: boolean) {
    accessToken.value = res.access_token
    refreshToken.value = res.refresh_token
    user.value = res.user
    sessionStorage.setItem(K_ACCESS, res.access_token)
    sessionStorage.setItem(K_USER, JSON.stringify(res.user))
    writeRefresh(res.refresh_token, remember)
  }

  function patchUser(patch: Partial<SessionUser>) {
    if (!user.value) return
    user.value = { ...user.value, ...patch }
    sessionStorage.setItem(K_USER, JSON.stringify(user.value))
  }

  function clear() {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    sessionStorage.removeItem(K_ACCESS)
    sessionStorage.removeItem(K_USER)
    localStorage.removeItem(K_REFRESH)
    sessionStorage.removeItem(K_REFRESH)
  }

  async function login(account: string, password: string, remember = true) {
    const res = await authApi.login({ account, password, remember })
    setSession(res, remember)
    return res
  }

  /** 刷新 access：内部单飞，失败返回 null（不抛异常，交给调用方决定跳转）。 */
  async function refresh(): Promise<string | null> {
    if (!refreshToken.value) return null
    if (refreshing) return refreshing
    refreshing = authApi
      .refresh(refreshToken.value)
      .then((res) => {
        accessToken.value = res.access_token
        sessionStorage.setItem(K_ACCESS, res.access_token)
        // refresh 轮换：新 token 沿用原来的存储位置
        const remember = !!localStorage.getItem(K_REFRESH)
        refreshToken.value = res.refresh_token
        writeRefresh(res.refresh_token, remember)
        return res.access_token
      })
      .catch(() => null)
      .finally(() => {
        refreshing = null
      })
    return refreshing
  }

  /** 刷新页面后静默续期，避免直接被踢到登录页。 */
  async function tryRefresh(): Promise<boolean> {
    if (accessToken.value) return true
    const token = await refresh()
    return !!token
  }

  async function logout() {
    const rt = refreshToken.value
    try {
      if (accessToken.value) await authApi.logout(rt || null)
    } catch {
      // 网络异常也要本地登出，不能把用户困在登录态
    } finally {
      clear()
    }
  }

  return {
    accessToken,
    refreshToken,
    user,
    isLogged,
    isLeader,
    displayName,
    roomText,
    setSession,
    patchUser,
    clear,
    login,
    refresh,
    tryRefresh,
    logout,
  }
})
