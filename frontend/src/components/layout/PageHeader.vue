<script setup lang="ts">
import { computed } from 'vue'
import BIcon from '@/components/base/BIcon.vue'

const props = withDefaults(
  defineProps<{
    kicker?: string
    title: string
    subtitle?: string
    back?: boolean
    right?: string
  }>(),
  { kicker: '', subtitle: '', back: false, right: '' },
)

const emit = defineEmits<{ (e: 'back'): void; (e: 'right'): void }>()

const titleSize = computed(() => (props.title.length > 12 ? '23px' : '28px'))
</script>

<template>
  <div class="head">
    <div v-if="back" class="backrow">
      <button type="button" class="backbtn" aria-label="返回" @click="emit('back')">
        <BIcon name="chev" :size="16" />
        <span>返回</span>
      </button>
      <button v-if="right" type="button" class="btn-text ink" @click="emit('right')">{{ right }}</button>
    </div>
    <div v-if="kicker" class="k-brand">{{ kicker }}</div>
    <div class="titlerow">
      <h1 class="big" :style="{ fontSize: titleSize }">{{ title }}</h1>
      <slot name="right" />
    </div>
    <p v-if="subtitle" class="sub">{{ subtitle }}</p>
    <slot />
  </div>
</template>

<style scoped>
.head {
  padding-top: 6px;
}
.backrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.backbtn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 4px 6px 4px 0;
}
.backbtn :deep(.ic) {
  transform: rotate(180deg);
}
.backbtn:active {
  opacity: 0.6;
}
.titlerow {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
}
.sub {
  font-size: 11px;
  color: var(--mute);
  margin-top: 6px;
  letter-spacing: 0.03em;
  line-height: 1.6;
}
</style>
