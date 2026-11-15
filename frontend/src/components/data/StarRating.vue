<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ modelValue?: number; readonly?: boolean; size?: number; label?: string }>(),
  { modelValue: 0, readonly: false, size: 18, label: '' },
)
const emit = defineEmits<{ (e: 'update:modelValue', v: number): void }>()

const stars = computed(() => [1, 2, 3, 4, 5])
const value = computed(() => Number(props.modelValue || 0))

function pick(n: number) {
  if (props.readonly) return
  emit('update:modelValue', n)
}
</script>

<template>
  <div class="stars" role="radiogroup" :aria-label="label || '评分'">
    <button
      v-for="n in stars"
      :key="n"
      type="button"
      class="star"
      :class="{ on: n <= value, ro: readonly }"
      :aria-label="`${n} 星`"
      :aria-checked="n === value"
      role="radio"
      :tabindex="readonly ? -1 : 0"
      @click="pick(n)"
      @keydown.enter.prevent="pick(n)"
      @keydown.space.prevent="pick(n)"
    >
      <svg :width="size" :height="size" viewBox="0 0 24 24" :fill="n <= value ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14 2 9.27l6.91-1.01z" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.star {
  padding: 4px 3px;
  min-width: 28px;
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ghost);
}
.star.on {
  color: var(--ink);
}
.star.ro {
  cursor: default;
}
.star:active:not(.ro) {
  opacity: 0.6;
}
</style>
