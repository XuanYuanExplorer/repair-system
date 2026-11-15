<script setup lang="ts">
withDefaults(
  defineProps<{
    name: string
    size?: number
    stroke?: number
  }>(),
  { size: 20, stroke: 1.7 },
)
</script>

<template>
  <svg
    class="ic"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    :stroke-width="stroke"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <use :href="`#i-${name}`" />
  </svg>
</template>

<style scoped>
.ic {
  flex: none;
  display: block;
}
</style>
