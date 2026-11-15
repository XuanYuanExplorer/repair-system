import { http } from './client'
import type { DeviceItem, LoginResult, StudentCheck } from './types'

export const authApi = {
  login: (payload: { account: string; password: string; remember: boolean }) =>
    http.post<LoginResult>('/auth/login', payload),

  refresh: (refreshToken: string) => http.post<{ access_token: string; refresh_token: string; expires_in: number }>('/auth/refresh', { refresh_token: refreshToken }),

  logout: (refreshToken: string | null) => http.post<{ logged_out: boolean }>('/auth/logout', { refresh_token: refreshToken }),

  checkStudent: (studentNo: string) => http.get<StudentCheck>('/auth/check-student', { params: { student_no: studentNo } }),

  register: (payload: { student_no: string; name: string; phone: string; password: string }) =>
    http.post<{ user_id: number; student_no: string; room: string; bed_no: number; bed_position: string }>('/auth/register', payload),

  smsCode: (phone: string, scene: 'reset' | 'bind' | 'register' = 'reset') =>
    http.post<{ sent: boolean; cooldown: number; retry_after: number; debug_code?: string }>('/auth/sms-code', { phone, scene }),

  resetPassword: (payload: { phone: string; code: string; new_password: string }) =>
    http.post<{ reset: boolean }>('/auth/reset-password', payload),

  changePassword: (payload: { old_password: string; new_password: string }) =>
    http.post<{ changed: boolean }>('/auth/change-password', payload),

  rebindPhone: (payload: { new_phone: string; old_code: string; new_code: string }) =>
    http.post<{ rebound: boolean }>('/auth/rebind-phone', payload),

  devices: () => http.get<DeviceItem[]>('/auth/devices'),

  revokeDevice: (id: number) => http.delete<{ revoked: boolean }>(`/auth/devices/${id}`),
}
