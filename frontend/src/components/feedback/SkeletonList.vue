<script setup lang="ts">
withDefaults(defineProps<{ rows?: number; variant?: 'card' | 'row' | 'detail' }>(), { rows: 3, variant: 'card' })
</script>

<template>
  <div class="sk" :class="variant" aria-hidden="true">
    <div v-for="i in rows" :key="i" class="item">
      <div class="skel l1" />
      <div class="skel l2" />
      <div v-if="variant !== 'row'" class="skel l3" />
    </div>
  </div>
</template>

<style scoped>
.sk {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 6px 0;
}
.item {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.card .item {
  border: 1px solid var(--hair);
  padding: 14px;
}
.row .item {
  border-bottom: 1px solid var(--hair);
  padding: 12px 0;
}
.detail .item {
  padding: 4px 0 10px;
}
.l1 {
  height: 9px;
  width: 34%;
}
.l2 {
  height: 14px;
  width: 72%;
}
.l3 {
  height: 8px;
  width: 48%;
}
</style>
