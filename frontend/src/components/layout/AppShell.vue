<script setup lang="ts">
import { onMounted } from 'vue'
import AppTabBar from './AppTabBar.vue'
import { useBadgeStore } from '@/stores/badge'

const props = withDefaults(
  defineProps<{ tab?: 'home' | 'repair' | 'payment' | 'profile' | null; bare?: boolean }>(),
  { tab: null, bare: false },
)

const badge = useBadgeStore()
onMounted(() => {
  if (!props.bare) badge.refresh()
})
</script>

<template>
  <div class="screen">
    <main class="body" :class="{ bare, 'has-tab': !!tab }">
      <slot />
    </main>
    <AppTabBar v-if="tab" :active="tab" />
  </div>
</template>

<style scoped>
.body.bare {
  padding: 0;
}
</style>
