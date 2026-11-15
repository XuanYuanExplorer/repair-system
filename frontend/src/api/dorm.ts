import { http } from './client'
import type { AssetItem, MembersResult, MyRoom } from './types'

export const dormApi = {
  myRoom: () => http.get<MyRoom>('/dorm/my-room'),

  members: () => http.get<MembersResult>('/dorm/members'),

  rules: () => http.get<{ room_id: number; can_edit: boolean; items: { seq: number; content: string }[] }>('/dorm/rules'),

  saveRules: (items: string[]) => http.put<{ items: { seq: number; content: string }[] }>('/dorm/rules', { items }),

  assets: () => http.get<AssetItem[]>('/dorm/assets'),

  borrowAsset: (id: number) => http.post<AssetItem>(`/dorm/assets/${id}/borrow`),

  returnAsset: (id: number) => http.post<AssetItem>(`/dorm/assets/${id}/return`),

  createRoomChange: (payload: { req_type: 'checkin' | 'checkout' | 'swap'; target_room?: string; reason?: string }) =>
    http.post<{ id: number; status: string }>('/dorm/room-change-requests', payload),
}
