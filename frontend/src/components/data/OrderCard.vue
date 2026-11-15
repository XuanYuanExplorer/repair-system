<script setup lang="ts">
import { computed } from 'vue'
import StatusTag from './StatusTag.vue'
import ProgressSteps from './ProgressSteps.vue'
import BIcon from '@/components/base/BIcon.vue'
import { fmtDay } from '@/utils/format'
import type { OrderBrief } from '@/api/types'

const props = withDefaults(defineProps<{ order: OrderBrief; active?: boolean }>(), { active: false })
const emit = defineEmits<{ (e: 'open'): void }>()

const showProgress = computed(() => ['pending', 'assigned', 'fixing', 'verify'].includes(props.order.status))
const done = computed(() => props.order.status === 'done')
</script>

<template>
  <div class="card" :class="{ active, muted: order.status === 'cancelled' }" @click="emit('open')">
    <div class="top">
      <span class="no">{{ order.order_no }}</span>
      <StatusTag :status="order.status" size="sm" />
    </div>
    <div class="title">{{ order.title }}</div>
    <div class="meta">
      <span>{{ order.submitted_text }}</span>
      <span v-if="order.is_timeout" class="tag red sm">超时</span>
      <span v-if="order.repair_round > 1" class="tag sm">返修 {{ order.repair_round - 1 }}</span>
    </div>

    <template v-if="showProgress">
      <ProgressSteps :status="order.status" :percent="order.percent" />
      <div v-if="order.expect_text" class="expect">{{ order.expect_text }}</div>
    </template>

    <div v-if="done" class="done-row">
      <span class="meta">{{ order.duration_days != null ? `处理 ${order.duration_days} 天 · ${fmtDay(order.created_at)} 提交` : '' }}</span>
      <span v-if="order.rating" class="rating">
        <BIcon name="star" :size="12" />
        <span class="num-lg">{{ Number(order.rating).toFixed(1) }}</span>
      </span>
      <span v-else class="mini-red">待评价</span>
    </div>
  </div>
</template>

<style scoped>
.card {
  border: var(--line) solid var(--ink);
  border-bottom: none;
  padding: 13px 14px;
  cursor: pointer;
  transition: background 0.15s;
}
.card:last-child {
  border-bottom: var(--line) solid var(--ink);
}
.card.muted {
  border-color: var(--hair);
  border-top-color: var(--hair);
  background: #fff;
}
.card.muted + .card {
  border-top-color: var(--ink);
}
.card.active {
  background: var(--panel);
}
.card:active {
  opacity: 0.7;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.no {
  font-size: 9px;
  letter-spacing: 0.16em;
  color: #b9b9b7;
  font-weight: 700;
}
.title {
  font-weight: 800;
  font-size: 13.5px;
  margin-top: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.meta {
  font-size: 10px;
  color: var(--mute);
  letter-spacing: 0.03em;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.expect {
  font-size: 9px;
  letter-spacing: 0.02em;
  color: var(--ink);
  margin-top: 3px;
  font-weight: 700;
  text-align: right;
}
.done-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.rating {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 13px;
}
.mini-red {
  font-size: 9px;
  color: var(--red);
  font-weight: 800;
  letter-spacing: 0.1em;
}
</style>
