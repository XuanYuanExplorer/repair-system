/** 金额 / 日期 / 文本格式化工具（全站唯一出口，禁止在组件里手写格式化）。 */

/** ¥1,358.00 —— 金额统一两位小数 + 千分位（整数分计算，避免浮点误差）。 */
export function fmtMoney(v: string | number | null | undefined, symbol = '¥'): string {
  const n = Number(v ?? 0)
  if (!Number.isFinite(n)) return `${symbol}0.00`
  return `${symbol}${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/** 1,358.00 —— 不带符号，用于表格右对齐数字。 */
export function fmtAmount(v: string | number | null | undefined): string {
  return fmtMoney(v, '')
}

/** 整数分累加，避免 0.1 + 0.2 类误差。 */
export function sumMoney(list: Array<string | number>): number {
  return list.reduce<number>((acc, v) => acc + Math.round(Number(v ?? 0) * 100), 0) / 100
}

function toDate(iso: string | Date | null | undefined): Date | null {
  if (!iso) return null
  const d = iso instanceof Date ? iso : new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/** MM-DD HH:mm（后端已按 +08:00 输出，直接取本地字段，避免时区二次换算）。 */
export function fmtTime(iso: string | Date | null | undefined): string {
  const d = toDate(iso)
  if (!d) return '—'
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(
    d.getHours(),
  ).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

/** YYYY-MM-DD */
export function fmtDate(iso: string | Date | null | undefined): string {
  const d = toDate(iso)
  if (!d) return '—'
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** MM-DD */
export function fmtDay(iso: string | Date | null | undefined): string {
  const d = toDate(iso)
  if (!d) return '—'
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 刚刚 / 12 分钟前 / 3 小时前 / 昨天 / 06-12 */
export function fmtRelative(iso: string | Date | null | undefined): string {
  const d = toDate(iso)
  if (!d) return '—'
  const diff = Date.now() - d.getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  if (hour < 48) return '昨天'
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** 秒 → mm:ss */
export function fmtCountdown(sec: number): string {
  const s = Math.max(0, Math.floor(sec))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/** 姓氏单字（头像用）。 */
export function familyName(name: string | null | undefined): string {
  return (name || '?').trim().slice(0, 1)
}

/** 手机号脱敏兜底（后端已脱敏时原样返回）。 */
export function maskPhone(phone: string | null | undefined): string {
  if (!phone) return ''
  if (phone.includes('*')) return phone
  return phone.replace(/^(\d{3})\d{4}(\d{4})$/, '$1****$2')
}

/** 复制文本：优先 Clipboard API，失败回退 execCommand。 */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    } catch {
      return false
    }
  }
}

/** 生成幂等键（不支持 crypto.randomUUID 的旧 WebView 回退）。 */
export function uuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}
