<script setup lang="ts">
import BIcon from '@/components/base/BIcon.vue'

withDefaults(defineProps<{ message?: string }>(), { message: '加载失败，请稍后重试' })
const emit = defineEmits<{ (e: 'retry'): void }>()
</script>

<template>
  <div class="err">
    <BIcon name="alert" :size="22" :stroke="1.5" />
    <p>{{ message }}</p>
    <button type="button" class="btn ghost sm" @click="emit('retry')">重新加载</button>
  </div>
</template>

<style scoped>
.err {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 34px 16px;
  color: var(--mute);
  text-align: center;
}
.err p {
  font-size: 11.5px;
  line-height: 1.6;
}
.err .btn {
  width: auto;
  padding: 8px 20px;
  font-size: 10px;
  margin-top: 0;
}
</style>
