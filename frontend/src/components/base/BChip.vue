<script setup lang="ts">
withDefaults(defineProps<{ on?: boolean; warn?: boolean; disabled?: boolean }>(), { on: false, warn: false, disabled: false })
const emit = defineEmits<{ (e: 'click'): void }>()
</script>

<template>
  <button type="button" class="chip" :class="{ on, warn }" :disabled="disabled" :aria-pressed="on" @click="emit('click')">
    <slot />
  </button>
</template>
