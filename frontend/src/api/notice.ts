import { http } from './client'
import type { Notice, NoticeList } from './types'

export const noticeApi = {
  list: (params?: { page?: number; page_size?: number }) => http.get<NoticeList>('/notices', { params }),

  detail: (id: number | string) => http.get<Notice>(`/notices/${id}`),

  read: (id: number) => http.post<{ read: boolean }>(`/notices/${id}/read`),

  receipt: (id: number) => http.post<{ receipt_at: string }>(`/notices/${id}/receipt`),
}
