/**
 * Axios 实例：统一响应解包 + 401 单飞刷新 + 429/5xx 提示。
 * 认证能力通过 setAuthBridge 注入，避免 client ↔ store ↔ router 的循环依赖。
 */
import axios, { type AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { useUiStore } from '@/stores/ui'
import type { Envelope } from './types'

export class BizError extends Error {
  code: number
  traceId: string
  data: unknown
  constructor(code: number, message: string, traceId = '', data: unknown = null) {
    super(message)
    this.name = 'BizError'
    this.code = code
    this.traceId = traceId
    this.data = data
  }
}

interface AuthBridge {
  getToken: () => string | null
  refresh: () => Promise<string | null>
  onLost: () => void
}

let bridge: AuthBridge = { getToken: () => null, refresh: async () => null, onLost: () => {} }
export function setAuthBridge(b: AuthBridge) {
  bridge = b
}

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 15000,
  headers: { 'X-Client': 'h5/1.1' },
})

client.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const token = bridge.getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

/** 单飞刷新：并发请求共享同一个 refresh Promise，避免刷新风暴。 */
let refreshing: Promise<string | null> | null = null

client.interceptors.response.use(
  (res) => {
    // 文件流（CSV / PDF）不是统一响应包，返回完整响应以便读取 content-disposition
    if (res.config.responseType === 'blob') return res
    const body = res.data as Envelope<unknown>
    if (!body || typeof body.code !== 'number') return res.data
    if (body.code === 0) return body.data as never
    return Promise.reject(new BizError(body.code, body.message, body.trace_id, body.data)) as never
  },
  async (err: AxiosError<Envelope<unknown>>) => {
    const cfg = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    const status = err.response?.status
    const ui = useUiStore()

    if (status === 401 && cfg && !cfg._retry) {
      cfg._retry = true
      refreshing ??= bridge.refresh().finally(() => {
        refreshing = null
      })
      const token = await refreshing
      if (token) {
        cfg.headers.Authorization = `Bearer ${token}`
        return client.request(cfg)
      }
      bridge.onLost()
      return Promise.reject(err)
    }

    const body = err.response?.data
    if (body && typeof body.code === 'number' && body.code !== 0) {
      return Promise.reject(new BizError(body.code, body.message, body.trace_id, body.data))
    }
    if (status === 429) ui.toast('操作太频繁，请稍后再试')
    else if (!err.response) ui.toast('网络异常，请检查网络后重试')
    else if (status && status >= 500) ui.toast('服务暂时不可用，请稍后再试')
    return Promise.reject(err)
  },
)

/** 便捷方法：返回值已解包为 data。 */
export const http = {
  get: <T>(url: string, config?: AxiosRequestConfig) => client.get(url, config) as unknown as Promise<T>,
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    client.post(url, data, config) as unknown as Promise<T>,
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) => client.put(url, data, config) as unknown as Promise<T>,
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    client.patch(url, data, config) as unknown as Promise<T>,
  delete: <T>(url: string, config?: AxiosRequestConfig) => client.delete(url, config) as unknown as Promise<T>,
  /** 文件下载：返回 Blob 与服务端文件名（content-disposition 解析）。 */
  download: async (url: string, config?: AxiosRequestConfig, fallback = 'download') => {
    const res = (await client.get(url, { ...config, responseType: 'blob' })) as unknown as {
      data: Blob
      headers: Record<string, string>
    }
    return { blob: res.data, filename: filenameFrom(res.headers?.['content-disposition'], fallback) }
  },
}

/** 从 content-disposition 中解析文件名（兼容 filename* 的 RFC 5987 编码）。 */
export function filenameFrom(disposition: string | undefined, fallback: string): string {
  if (!disposition) return fallback
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition)
  if (star) return decodeURIComponent(star[1])
  const plain = /filename="?([^";]+)"?/i.exec(disposition)
  return plain ? decodeURIComponent(plain[1]) : fallback
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

export function isBizError(e: unknown): e is BizError {
  return e instanceof BizError
}

/** 从异常中提取可展示文案。 */
export function errText(e: unknown, fallback = '操作失败，请稍后重试'): string {
  if (e instanceof BizError) return e.message || fallback
  if (e instanceof Error && e.message) return e.message
  return fallback
}
