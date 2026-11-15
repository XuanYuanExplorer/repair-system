<script setup lang="ts">
withDefaults(defineProps<{ cn: string; en?: string; action?: string }>(), { en: '', action: '' })
const emit = defineEmits<{ (e: 'action'): void }>()
</script>

<template>
  <div class="sec">
    <span class="l">
      <span class="h-cn">{{ cn }}</span>
      <span v-if="en" class="h-en">{{ en }}</span>
    </span>
    <button v-if="action" type="button" class="all" @click="emit('action')">{{ action }}</button>
    <slot name="right" />
  </div>
</template>

<style scoped>
.all {
  padding: 0;
}
</style>
