<script setup lang="ts">
import BIcon from '@/components/base/BIcon.vue'

withDefaults(defineProps<{ title: string; desc?: string; actionText?: string; icon?: string }>(), {
  desc: '',
  actionText: '',
  icon: 'doc',
})
const emit = defineEmits<{ (e: 'action'): void }>()
</script>

<template>
  <div class="empty">
    <BIcon :name="icon" :size="26" :stroke="1.4" />
    <p class="title">{{ title }}</p>
    <p v-if="desc" class="desc">{{ desc }}</p>
    <button v-if="actionText" type="button" class="btn ghost sm act" @click="emit('action')">{{ actionText }}</button>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 38px 20px;
  color: var(--ghost);
  text-align: center;
}
.title {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--mute);
  letter-spacing: 0.02em;
}
.desc {
  font-size: 10.5px;
  color: var(--ghost);
  line-height: 1.6;
}
.act {
  width: auto;
  padding: 8px 22px;
  margin-top: 6px;
  font-size: 10px;
}
</style>
