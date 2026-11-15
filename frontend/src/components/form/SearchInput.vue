<script setup lang="ts">
import BIcon from '@/components/base/BIcon.vue'

withDefaults(defineProps<{ placeholder?: string; modelValue?: string }>(), { placeholder: '搜索', modelValue: '' })
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void; (e: 'submit'): void }>()
</script>

<template>
  <label class="search">
    <BIcon name="search" :size="15" />
    <input
      :value="modelValue"
      type="search"
      :placeholder="placeholder"
      enterkeyhint="search"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @keyup.enter="emit('submit')"
    />
    <button v-if="modelValue" type="button" class="clear" aria-label="清空" @click="emit('update:modelValue', '')">
      <BIcon name="close" :size="12" />
    </button>
  </label>
</template>

<style scoped>
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  border: var(--line) solid var(--ink);
  padding: 9px 12px;
  cursor: text;
  color: var(--ink);
  margin-top: 14px;
}
input {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}
input::placeholder {
  color: var(--ghost);
  font-weight: 500;
}
input::-webkit-search-cancel-button {
  display: none;
}
.clear {
  padding: 2px;
  color: var(--mute);
  flex: none;
}
</style>
