/** 前端校验：与后端 auth_service.password_strength 保持同一套规则。 */

export type Strength = 'weak' | 'medium' | 'strong'

export const STRENGTH_LABEL: Record<Strength, { cn: string; en: string; level: number }> = {
  weak: { cn: '弱', en: 'WEAK', level: 1 },
  medium: { cn: '中', en: 'MEDIUM', level: 2 },
  strong: { cn: '强', en: 'STRONG', level: 3 },
}

/**
 * 长度 <6 或纯数字/纯字母 → 弱（不可提交）
 * ≥6 且含字母+数字 → 中
 * ≥8 且含字母+数字+符号 → 强
 */
export function passwordStrength(pwd: string): Strength {
  const hasLetter = /[A-Za-z]/.test(pwd)
  const hasDigit = /\d/.test(pwd)
  const hasSymbol = /[^A-Za-z0-9]/.test(pwd)
  if (pwd.length < 6 || !hasLetter || !hasDigit) return 'weak'
  if (pwd.length >= 8 && hasSymbol) return 'strong'
  return 'medium'
}

export function isPhone(v: string): boolean {
  return /^1[3-9]\d{9}$/.test(v)
}

export function isStudentNo(v: string): boolean {
  return /^\d{8,12}$/.test(v)
}

export function isEmail(v: string): boolean {
  return /^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(v)
}

/** 长度按字符计（中文一字算一，与后端 len() 一致）。 */
export function charLen(v: string): number {
  return Array.from(v || '').length
}
