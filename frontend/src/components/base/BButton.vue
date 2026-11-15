<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'solid' | 'ghost' | 'ghost-red' | 'red'
    size?: 'md' | 'sm'
    block?: boolean
    loading?: boolean
    disabled?: boolean
    type?: 'button' | 'submit'
  }>(),
  { variant: 'solid', size: 'md', block: true, loading: false, disabled: false, type: 'button' },
)

const emit = defineEmits<{ (e: 'click', ev: MouseEvent): void }>()
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="[variant, size === 'sm' ? 'sm' : '', block ? '' : 'inline']"
    :disabled="disabled || loading"
    :aria-busy="loading"
    @click="emit('click', $event)"
  >
    <span v-if="loading" class="spin" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.spin {
  width: 12px;
  height: 12px;
  border: 1.5px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: rot 0.7s linear infinite;
}
@keyframes rot {
  to {
    transform: rotate(360deg);
  }
}
</style>
