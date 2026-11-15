<script setup lang="ts">
import BIcon from '@/components/base/BIcon.vue'
import type { Facility } from '@/api/types'

defineProps<{ facility: Facility }>()
const emit = defineEmits<{ (e: 'repair'): void }>()

const ICONS: Record<string, string> = {
  ac: 'zap',
  water: 'drop',
  furniture: 'clip',
  network: 'wifi2',
  door: 'lock',
  public: 'grid',
}
</script>

<template>
  <div class="row" :class="{ fault: facility.status === 'fault' }">
    <span class="name">
      <BIcon :name="ICONS[facility.category] || 'tool'" :size="16" />
      <span>
        {{ facility.name }}
        <span class="sub">{{ facility.status_label }}<template v-if="facility.enabled_year"> · {{ facility.enabled_year }} 年启用</template></span>
      </span>
    </span>
    <button v-if="facility.status === 'fault'" type="button" class="btn-text" @click="emit('repair')">去报修</button>
    <span v-else class="tick">正常</span>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--hair);
}
.row:last-child {
  border-bottom: none;
}
.name {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  font-weight: 700;
}
.sub {
  display: block;
  font-size: 9.5px;
  color: var(--mute);
  font-weight: 600;
  margin-top: 2px;
  letter-spacing: 0.03em;
}
.fault .name {
  color: var(--red);
}
.tick {
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--mute);
  font-weight: 700;
}
</style>
