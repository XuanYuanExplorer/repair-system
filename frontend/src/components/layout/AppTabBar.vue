<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBadgeStore } from '@/stores/badge'

const props = defineProps<{ active?: 'home' | 'repair' | 'payment' | 'profile' | null }>()
const route = useRoute()
const router = useRouter()
const badge = useBadgeStore()

const tabs = computed(() => [
  { key: 'home', label: '首页', to: '/' },
  { key: 'repair', label: '报修', to: '/repair/list' },
  { key: 'payment', label: '缴费', to: '/payment' },
  { key: 'profile', label: '我的', to: '/profile' },
])

const current = computed(() => props.active ?? (route.meta.tab as string) ?? '')
const showDot = computed(() => badge.unreadTotal > 0)

function go(to: string) {
  if (route.path !== to) router.push(to)
}
</script>

<template>
  <nav class="tabbar" aria-label="主导航">
    <button
      v-for="t in tabs"
      :key="t.key"
      type="button"
      class="tab"
      :class="{ on: current === t.key }"
      :aria-current="current === t.key ? 'page' : undefined"
      @click="go(t.to)"
    >
      {{ t.label }}
      <span v-if="t.key === 'profile' && showDot" class="rd" />
    </button>
  </nav>
</template>
