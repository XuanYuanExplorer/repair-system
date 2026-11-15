<script setup lang="ts">
import BTag from '@/components/base/BTag.vue'
import type { SlotItem } from '@/api/types'

defineProps<{ slots: SlotItem[]; modelValue: string; loading?: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <div class="list">
    <div v-for="s in slots" :key="s.code" class="row" :class="{ full: s.full, on: modelValue === s.code }">
      <button type="button" class="pick" :disabled="s.full" @click="emit('update:modelValue', s.code)">
        <span class="label" :class="{ strike: s.full }">{{ s.label }}</span>
        <BTag v-if="modelValue === s.code" tone="red" sm class="sel">已选</BTag>
      </button>
      <span class="hint" :class="{ red: s.full }">{{ s.full ? '已约满' : `可约 · 余 ${s.left}` }}</span>
    </div>
    <p v-if="!slots.length && !loading" class="empty">暂无可约时段，请选择其他日期</p>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid var(--hair);
}
.row:last-of-type {
  border-bottom: none;
}
.pick {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  text-align: left;
}
.label {
  font-size: 12px;
}
.row.on .label {
  font-weight: 800;
}
.strike {
  color: var(--mute);
  text-decoration: line-through;
}
.hint {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--mute);
  font-weight: 700;
  flex: none;
}
.empty {
  font-size: 11px;
  color: var(--mute);
  padding: 10px 0;
}
</style>
