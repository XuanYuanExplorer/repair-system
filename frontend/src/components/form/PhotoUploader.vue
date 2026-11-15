<script setup lang="ts">
import { watch } from 'vue'
import BIcon from '@/components/base/BIcon.vue'
import { useUploader } from '@/composables/useUploader'
import { useUiStore } from '@/stores/ui'

const props = withDefaults(defineProps<{ max?: number; bizType?: string; modelValue?: string[] }>(), {
  max: 6,
  bizType: 'repair',
  modelValue: () => [],
})
const emit = defineEmits<{ (e: 'update:modelValue', v: string[]): void }>()

const ui = useUiStore()
const { items, urls, busy, full, addFiles, remove, retry } = useUploader({ max: props.max, bizType: props.bizType })

watch(urls, (v) => emit('update:modelValue', [...v]))

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  await addFiles(input.files)
  input.value = ''
  if (items.value.some((i) => i.status === 'error')) {
    const first = items.value.find((i) => i.status === 'error')
    if (first?.error) ui.toast(first.error, 'red')
  }
}
</script>

<template>
  <div class="grid">
    <div v-for="it in items" :key="it.id" class="cell" :class="it.status">
      <img v-if="it.preview" :src="it.preview" alt="" loading="lazy" decoding="async" />
      <div v-else class="ph"><BIcon name="cam" :size="14" /></div>

      <div v-if="it.status === 'uploading'" class="mask">
        <span class="pct num-lg">{{ it.progress }}%</span>
      </div>
      <button v-if="it.status === 'error'" type="button" class="retry" @click="retry(it.id)">重试</button>
      <button type="button" class="del" aria-label="删除" @click="remove(it.id)">
        <BIcon name="close" :size="10" />
      </button>
    </div>

    <label v-if="!full" class="add" :class="{ busy }">
      <BIcon name="cam" :size="16" />
      <span class="txt">{{ busy ? '上传中' : '添加' }}</span>
      <input type="file" accept="image/jpeg,image/png,image/webp,video/mp4" multiple hidden :disabled="busy" @change="onPick" />
    </label>
  </div>
</template>

<style scoped>
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cell,
.add {
  width: 58px;
  height: 58px;
  flex: none;
  position: relative;
  background: var(--panel);
  border: 1px solid var(--hair);
  overflow: hidden;
}
.cell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ph {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ghost);
}
.cell.error {
  border-color: var(--red);
}
.mask {
  position: absolute;
  inset: 0;
  background: rgba(16, 16, 16, 0.62);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
}
.pct {
  font-size: 11px;
}
.del {
  position: absolute;
  top: 0;
  right: 0;
  width: 16px;
  height: 16px;
  background: rgba(16, 16, 16, 0.72);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}
.retry {
  position: absolute;
  inset: 0;
  background: rgba(217, 59, 59, 0.86);
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
}
.add {
  border: var(--line) dashed var(--dash);
  background: #fff;
  color: #b9b9b7;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  cursor: pointer;
}
.add.busy {
  opacity: 0.5;
  cursor: not-allowed;
}
.txt {
  font-size: 8.5px;
  letter-spacing: 0.14em;
  font-weight: 700;
}
</style>
