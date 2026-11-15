<script setup lang="ts">
withDefaults(defineProps<{ disabled?: boolean; label?: string }>(), { disabled: false, label: '' })
const model = defineModel<boolean>({ default: false })
</script>

<template>
  <span
    class="sw"
    :class="{ on: model, disabled }"
    role="switch"
    :aria-checked="model"
    :aria-label="label || undefined"
    :aria-disabled="disabled"
    tabindex="0"
    @click="!disabled && (model = !model)"
    @keydown.space.prevent="!disabled && (model = !model)"
  />
</template>
