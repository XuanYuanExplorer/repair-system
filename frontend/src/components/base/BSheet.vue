<script setup lang="ts">
import { watch, onUnmounted } from 'vue'
import BIcon from './BIcon.vue'

withDefaults(defineProps<{ title?: string; height?: string }>(), { title: '', height: 'auto' })
const open = defineModel<boolean>('modelValue', { default: false })

watch(open, (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
})
onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="mask" @click.self="open = false">
        <div class="sheet" :style="{ maxHeight: height }" role="dialog" aria-modal="true">
          <div class="sheet-head">
            <span class="h-cn">{{ title }}</span>
            <button type="button" class="close" aria-label="关闭" @click="open = false">
              <BIcon name="close" :size="16" />
            </button>
          </div>
          <div class="sheet-body"><slot /></div>
          <div v-if="$slots.footer" class="sheet-foot"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(16, 16, 16, 0.32);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 80;
}
.sheet {
  width: 100%;
  max-width: 100%;
  background: #fff;
  border-top: var(--line) solid var(--ink);
  display: flex;
  flex-direction: column;
  padding-bottom: env(safe-area-inset-bottom);
  animation: rise 0.2s ease;
}
@keyframes rise {
  from {
    transform: translateY(12px);
    opacity: 0.6;
  }
}
.sheet-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 22px 10px;
  border-bottom: 1px solid var(--hair);
  flex: none;
}
.sheet-body {
  padding: 6px 22px 18px;
  overflow-y: auto;
}
.sheet-foot {
  padding: 0 22px 18px;
  flex: none;
}
.close {
  padding: 4px;
}
</style>
