import { http } from './client'
import type { Faq, Hotline } from './types'

export const helpApi = {
  faqs: (q?: string) => http.get<Faq[]>('/help/faqs', { params: q ? { q } : {} }),
  hotlines: () => http.get<Hotline[]>('/help/hotlines'),
}
