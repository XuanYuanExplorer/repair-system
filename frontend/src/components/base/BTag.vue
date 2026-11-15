<script setup lang="ts">
withDefaults(defineProps<{ text?: string; tone?: 'ink' | 'red' | 'solid' | 'gray'; sm?: boolean }>(), {
  text: '',
  tone: 'ink',
  sm: false,
})
</script>

<template>
  <span class="tag" :class="[tone === 'red' ? 'red' : tone === 'solid' ? 'blk' : tone === 'gray' ? 'gray' : '', sm ? 'sm' : '']">
    <slot>{{ text }}</slot>
  </span>
</template>
