import { http } from './client'
import type { Profile } from './types'

export const profileApi = {
  get: () => http.get<Profile>('/profile'),

  update: (payload: { avatar_url?: string | null; gender?: number; emergency_name?: string; emergency_phone?: string; email?: string }) =>
    http.put<Profile>('/profile', payload),
}
