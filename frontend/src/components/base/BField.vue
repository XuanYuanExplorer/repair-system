<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    type?: string
    placeholder?: string
    error?: string
    disabled?: boolean
    maxlength?: number
    inputmode?: 'text' | 'numeric' | 'tel' | 'email'
    autocomplete?: string
    suffix?: string
    name?: string
  }>(),
  { type: 'text', placeholder: '', error: '', disabled: false, maxlength: 64, inputmode: 'text', autocomplete: 'off', suffix: '', name: '' },
)

const model = defineModel<string>({ default: '' })
const emit = defineEmits<{ (e: 'blur'): void; (e: 'suffix'): void; (e: 'enter'): void }>()
</script>

<template>
  <label class="field" :class="{ err: !!error }">
    <span class="label">{{ label }}</span>
    <input
      v-model="model"
      class="v"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :maxlength="maxlength"
      :inputmode="inputmode"
      :autocomplete="autocomplete"
      :name="name"
      :aria-invalid="!!error"
      @blur="emit('blur')"
      @keyup.enter="emit('enter')"
    />
    <button v-if="suffix" type="button" class="act" @click.prevent="emit('suffix')">{{ suffix }}</button>
    <slot name="suffix" />
  </label>
  <p v-if="error" class="errmsg">▲ {{ error }}</p>
</template>

<style scoped>
.field {
  position: relative;
  cursor: text;
}
.label {
  font-size: 9px;
  letter-spacing: 0.18em;
  font-weight: 700;
  color: var(--mute);
  width: 52px;
  flex: none;
  text-transform: uppercase;
}
.v {
  font-size: 14px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
}
.act {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  flex: none;
  padding: 4px 0 4px 8px;
}
.errmsg {
  color: var(--red);
  font-size: 9px;
  letter-spacing: 0.08em;
  font-weight: 700;
  margin-top: 6px;
}
</style>
