<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <div class="toasts" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="t in ui.toasts" :key="t.id" class="toast" :class="{ red: t.tone === 'red' }">
        {{ t.text }}
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  left: 50%;
  bottom: calc(84px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  pointer-events: none;
  width: max-content;
  max-width: 88vw;
}
.toast {
  background: var(--ink);
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 10px 16px;
  line-height: 1.5;
  text-align: center;
  border: 1.5px solid var(--ink);
}
.toast.red {
  background: #fff;
  color: var(--red);
  border-color: var(--red);
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
