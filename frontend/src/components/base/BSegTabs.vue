<script setup lang="ts">
defineProps<{ items: { value: string; label: string }[] }>()
const model = defineModel<string>({ default: '' })
</script>

<template>
  <div class="seg" role="tablist">
    <button
      v-for="it in items"
      :key="it.value"
      type="button"
      role="tab"
      :aria-selected="model === it.value"
      :class="{ on: model === it.value }"
      @click="model = it.value"
    >
      {{ it.label }}
    </button>
  </div>
</template>
