import { http } from './client'
import type { HomeSummary, PublicNotice } from './types'

export const homeApi = {
  summary: () => http.get<HomeSummary>('/home/summary'),
  latestNotices: () => http.get<PublicNotice[]>('/public/notices/latest'),
  meta: () => http.get<{ app_name: string; env: string; pay_provider: string; sms_provider: string; school: string }>('/meta'),
}
