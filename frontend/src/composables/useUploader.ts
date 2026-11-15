import { computed, ref } from 'vue'
import { fileApi } from '@/api/files'
import { errText } from '@/api/client'

export interface UploadItem {
  id: number
  status: 'uploading' | 'done' | 'error'
  progress: number
  preview: string
  url: string
  file: File
  error?: string
}

const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']
const VIDEO_TYPES = ['video/mp4']
const MAX_IMAGE_MB = 8
const MAX_VIDEO_MB = 30

let seq = 0

/** 客户端压缩：长边 1600px、质量 0.8，显著降低 4G 上传耗时；HEIC 交给服务端原样存。 */
async function compress(file: File): Promise<File> {
  if (!file.type.startsWith('image/') || file.type.includes('heic') || file.size < 400 * 1024) return file
  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height))
    if (scale >= 1 && file.size < 1024 * 1024) return file
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.8))
    if (!blob) return file
    return new File([blob], file.name.replace(/\.\w+$/, '.jpg'), { type: 'image/jpeg' })
  } catch {
    return file
  }
}

/**
 * 多图 / 视频上传：数量限制、压缩、单张进度、失败单独重试。
 * 返回的 urls 只包含上传成功的地址，可直接提交给业务接口。
 */
export function useUploader(opts: { max?: number; bizType?: string } = {}) {
  const { max = 6, bizType = 'repair' } = opts
  const items = ref<UploadItem[]>([])
  const urls = computed(() => items.value.filter((i) => i.status === 'done').map((i) => i.url))
  const busy = computed(() => items.value.some((i) => i.status === 'uploading'))
  const full = computed(() => items.value.length >= max)

  function validate(file: File): string | null {
    const isImage = IMAGE_TYPES.includes(file.type)
    const isVideo = VIDEO_TYPES.includes(file.type)
    if (!isImage && !isVideo) return '仅支持 JPG / PNG / WEBP / MP4'
    if (isVideo && file.size > MAX_VIDEO_MB * 1024 * 1024) return `视频不超过 ${MAX_VIDEO_MB}MB`
    if (isImage && file.size > MAX_IMAGE_MB * 1024 * 1024) return `图片不超过 ${MAX_IMAGE_MB}MB`
    return null
  }

  async function upload(item: UploadItem) {
    item.status = 'uploading'
    item.progress = 0
    try {
      const raw = await compress(item.file)
      const res = await fileApi.upload(raw, bizType, (p) => (item.progress = p))
      item.url = res.url
      item.status = 'done'
      item.progress = 100
    } catch (e) {
      item.status = 'error'
      item.error = errText(e, '上传失败')
    }
  }

  /** 并发 2 张，避免弱网下大量请求互相拖慢。 */
  async function addFiles(files: File[] | FileList) {
    const list = Array.from(files)
    const accepted: UploadItem[] = []
    for (const file of list) {
      if (items.value.length >= max) break
      const err = validate(file)
      if (err) {
        accepted.push({ id: ++seq, status: 'error', progress: 0, preview: '', url: '', file, error: err })
        continue
      }
      accepted.push({
        id: ++seq,
        status: 'uploading',
        progress: 0,
        preview: URL.createObjectURL(file),
        url: '',
        file,
      })
    }
    items.value = [...items.value, ...accepted]
    const pending = accepted.filter((i) => !i.error)
    const queue = [...pending]
    const workers = Array.from({ length: Math.min(2, queue.length) }, async () => {
      while (queue.length) {
        const next = queue.shift()
        if (next) await upload(next)
      }
    })
    await Promise.all(workers)
  }

  function remove(id: number) {
    const target = items.value.find((i) => i.id === id)
    if (target?.preview) URL.revokeObjectURL(target.preview)
    items.value = items.value.filter((i) => i.id !== id)
  }

  function retry(id: number) {
    const item = items.value.find((i) => i.id === id)
    if (item && item.status === 'error' && !item.error?.includes('仅支持') && !item.error?.includes('不超过')) {
      void upload(item)
    }
  }

  function reset() {
    items.value.forEach((i) => i.preview && URL.revokeObjectURL(i.preview))
    items.value = []
  }

  return { items, urls, busy, full, addFiles, remove, retry, reset }
}
