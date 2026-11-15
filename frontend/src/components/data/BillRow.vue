<script setup lang="ts">
import { computed } from 'vue'
import BCheckbox from '@/components/base/BCheckbox.vue'
import { fmtMoney } from '@/utils/format'
import { BILL_STATUS, statusOf } from '@/utils/dict'
import type { Bill } from '@/api/types'

const props = withDefaults(
  defineProps<{ bill: Bill; checked?: boolean; selectable?: boolean; first?: boolean }>(),
  { checked: false, selectable: false, first: false },
)
const emit = defineEmits<{ (e: 'toggle'): void; (e: 'open'): void }>()

const status = computed(() => (props.bill.overdue_days > 0 ? { label: '已逾期', tone: 'red' as const } : statusOf(BILL_STATUS, props.bill.status)))
const mergeBlocked = computed(() => props.selectable && !props.bill.mergeable)
const dueUrgent = computed(() => props.bill.urgent)
</script>

<template>
  <div class="bill" :class="{ active: checked, first }" @click="emit('open')">
    <BCheckbox
      v-if="selectable"
      :model-value="checked"
      :disabled="mergeBlocked"
      class="ckbox"
      @click.stop="emit('toggle')"
    />
    <div class="main">
      <div class="title">{{ bill.title }}</div>
      <div class="sub">
        <span>{{ bill.due_text || bill.period }}</span>
        <span v-if="bill.late_fee !== '0.00'" class="red">· 含滞纳金 {{ fmtMoney(bill.late_fee) }}</span>
        <span v-if="mergeBlocked" class="mute">· 不可合并</span>
      </div>
    </div>
    <div class="right">
      <span class="num-lg amount">{{ fmtMoney(bill.total) }}</span>
      <span class="tag" :class="{ red: status.tone === 'red', gray: status.tone === 'gray' }">{{ status.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.bill {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
  border: 1px solid var(--hair);
  border-top: none;
  background: #fff;
  transition: background 0.15s;
  cursor: pointer;
}
.bill.first {
  border-top: var(--line) solid var(--ink);
}
.bill.active {
  border-color: var(--ink);
  background: var(--panel);
}
.bill.active + .bill {
  border-top-color: var(--ink);
}
.ckbox {
  flex: none;
}
.main {
  flex: 1;
  min-width: 0;
}
.title {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub {
  font-size: 10px;
  color: var(--mute);
  margin-top: 3px;
  letter-spacing: 0.02em;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex: none;
}
.amount {
  font-size: 19px;
}
</style>
