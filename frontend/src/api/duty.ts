import { http } from './client'
import type { DutySchedule, HygieneResult } from './types'

export const dutyApi = {
  schedule: (weekStart?: string) => http.get<DutySchedule>('/duty/schedule', { params: weekStart ? { week_start: weekStart } : {} }),

  generate: (weekStart?: string) => http.post<{ created: number; week_start: string }>('/duty/schedule/generate', { week_start: weekStart || null }),

  updateDay: (id: number, payload: { user_id?: number | null; areas?: string[] }) =>
    http.put<DutySchedule>(`/duty/schedule/${id}`, payload),

  rule: () => http.get<{ mode: string; member_order: number[]; areas: string[]; members: { id: number; name: string }[]; can_edit: boolean }>('/duty/rules'),

  checks: (params?: { page?: number; page_size?: number }) => http.get<HygieneResult>('/hygiene/checks', { params }),

  rectify: (checkId: number, mediaUrls: string[]) => http.post<{ status: string }>(`/hygiene/checks/${checkId}/rectify`, { media_urls: mediaUrls }),
}
