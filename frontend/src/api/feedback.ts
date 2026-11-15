import { http } from './client'
import type { Feedback, Page } from './types'

export const feedbackApi = {
  create: (payload: { type: string; order_id: number | null; content: string; media_urls: string[] }) =>
    http.post<{ id: number; fb_no: string }>('/feedbacks', payload),

  list: (params?: { page?: number; page_size?: number }) => http.get<Page<Feedback>>('/feedbacks', { params }),

  satisfaction: (id: number, score: number) => http.post<{ satisfaction: number }>(`/feedbacks/${id}/satisfaction`, { score }),
}
