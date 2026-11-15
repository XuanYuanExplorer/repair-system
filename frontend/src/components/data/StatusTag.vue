<script setup lang="ts">
import { computed } from 'vue'
import { ORDER_STATUS, statusOf } from '@/utils/dict'

const props = withDefaults(defineProps<{ status: string; size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
const item = computed(() => statusOf(ORDER_STATUS, props.status))
</script>

<template>
  <span class="tag" :class="[item.tone === 'red' ? 'red' : item.tone === 'gray' ? 'gray' : 'blk', size === 'sm' ? 'sm' : '', size === 'lg' ? 'lg' : '']">
    {{ item.label }}
  </span>
</template>

<style scoped>
.tag.lg {
  font-size: 10px;
  padding: 5px 10px;
}
</style>
