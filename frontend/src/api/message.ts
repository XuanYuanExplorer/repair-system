import { http } from './client'
import type { MessageList, MessagePreferences } from './types'

export const messageApi = {
  list: (params?: { type?: string; page?: number; page_size?: number }) => http.get<MessageList>('/messages', { params }),

  unreadCount: () => http.get<{ total: number; by_type: Record<string, number> }>('/messages/unread-count'),

  readOne: (id: number) => http.post<{ read: boolean }>(`/messages/${id}/read`),

  readAll: (type?: string) => http.post<{ updated: number }>('/messages/read-all', { type: type || null }),

  preferences: () => http.get<MessagePreferences>('/messages/preferences'),

  savePreferences: (payload: { sms_types: string[]; wechat_types: string[] }) =>
    http.put<MessagePreferences>('/messages/preferences', payload),
}
