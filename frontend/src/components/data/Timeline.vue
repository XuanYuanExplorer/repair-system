<script setup lang="ts">
import { fmtTime } from '@/utils/format'
import type { TimelineNode } from '@/api/types'

defineProps<{ items: TimelineNode[] }>()
</script>

<template>
  <div class="tl">
    <div v-for="(n, i) in items" :key="n.type + i" class="tl-i" :class="n.state">
      <div class="row">
        <span class="label" :class="{ act: n.state === 'active', todo: n.state === 'todo' }">{{ n.label }}</span>
        <span class="time">{{ n.at ? fmtTime(n.at) : '—' }}</span>
      </div>
      <div v-if="n.actor || n.note" class="meta">
        <span v-if="n.actor">{{ n.actor }}</span>
        <span v-if="n.note" class="note">· {{ n.note }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
}
.label {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.label.todo {
  color: var(--ghost);
  font-weight: 600;
}
.label.act {
  color: var(--red);
}
.time {
  font-size: 10px;
  color: var(--mute);
  font-variant-numeric: tabular-nums;
  flex: none;
}
.meta {
  font-size: 10px;
  color: var(--mute);
  margin-top: 3px;
  letter-spacing: 0.02em;
}
.note {
  margin-left: 2px;
}
</style>
