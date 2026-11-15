import { http } from './client'
import type { ArchiveResult, ChatMessage, OrderCreateResult, OrderDetail, OrderListResult, SlotResult } from './types'

export interface CreateOrderPayload {
  category: string
  location_type: 'in_room' | 'public'
  location_desc: string
  description: string
  media_urls: string[]
  preferred_date: string | null
  preferred_slot: string | null
  require_presence: boolean
  contact_phone: string
  client_request_id: string
}

export const repairApi = {
  slots: (date?: string) => http.get<SlotResult>('/repair/slots', { params: date ? { date } : {} }),

  create: (payload: CreateOrderPayload, idempotencyKey: string) =>
    http.post<OrderCreateResult>('/repair/orders', payload, { headers: { 'Idempotency-Key': idempotencyKey } }),

  list: (params: { status?: string; category?: string; keyword?: string; page?: number; page_size?: number }) =>
    http.get<OrderListResult>('/repair/orders', { params }),

  detail: (id: number | string) => http.get<OrderDetail>(`/repair/orders/${id}`),

  update: (id: number, payload: Partial<Pick<CreateOrderPayload, 'description' | 'preferred_date' | 'preferred_slot' | 'contact_phone' | 'require_presence'>>) =>
    http.patch<OrderDetail>(`/repair/orders/${id}`, payload),

  cancel: (id: number, reason?: string) => http.post<OrderDetail>(`/repair/orders/${id}/cancel`, { reason: reason || null }),

  urge: (id: number) => http.post<{ urged: boolean; retry_after: number }>(`/repair/orders/${id}/urge`),

  messages: (id: number, afterId?: number) =>
    http.get<{ items: ChatMessage[]; last_id: number }>(`/repair/orders/${id}/messages`, {
      params: afterId ? { after_id: afterId } : {},
    }),

  sendMessage: (id: number, content: string) => http.post<ChatMessage>(`/repair/orders/${id}/messages`, { content }),

  verify: (id: number, resolved: boolean, reason?: string) =>
    http.post<OrderDetail>(`/repair/orders/${id}/verify`, { resolved, reason: reason || null }),

  rate: (id: number, payload: { speed: number; attitude: number; quality: number; content?: string; is_anonymous: boolean }) =>
    http.post<{ rated: boolean; score: number }>(`/repair/orders/${id}/rate`, payload),

  archive: () => http.get<ArchiveResult>('/repair/archive'),
}
