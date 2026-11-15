import { client } from './client'
import type { UploadResult } from './types'

export const fileApi = {
  /** 单文件上传（multipart）。bizType 仅用于归档目录，不影响权限。 */
  upload: async (file: File, bizType = 'repair', onProgress?: (percent: number) => void): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    form.append('biz_type', bizType)
    const res = await client.post('/files', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    })
    return res as unknown as UploadResult
  },
}
