<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ status: string; showLabel?: boolean; percent?: number | null }>(), {
  showLabel: true,
  percent: null,
})

const STEPS = ['SUBMIT', 'ASSIGN', 'FIXING', 'VERIFY']
const INDEX: Record<string, number> = { pending: 0, assigned: 1, fixing: 2, verify: 3, done: 4, cancelled: 0 }

const current = computed(() => INDEX[props.status] ?? 0)
const width = computed(() => {
  if (props.percent != null) return Math.min(100, Math.max(props.percent, 4))
  return Math.min(100, Math.max((current.value / 4) * 100, 4))
})
</script>

<template>
  <div class="wrap">
    <div class="prog"><i :style="{ width: width + '%' }" /></div>
    <div v-if="showLabel" class="psteps">
      <span v-for="(s, i) in STEPS" :key="s" :class="{ on: i === Math.min(current, 3) }">{{ s }}</span>
    </div>
  </div>
</template>

<style scoped>
.wrap {
  width: 100%;
}
</style>
