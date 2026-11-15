<script setup lang="ts">
import { familyName } from '@/utils/format'
import type { Member } from '@/api/types'

defineProps<{ member: Member; index: number }>()
</script>

<template>
  <div class="row">
    <span class="left">
      <b class="idx num-lg">{{ index }}</b>
      <span class="avatar" :class="{ outline: index % 2 === 0 }">{{ familyName(member.name) }}</span>
      <span class="who">
        <span class="nameline">
          <b>{{ member.name }}</b>
          <span v-if="member.is_me" class="me">（我）</span>
          <span v-if="member.is_leader" class="tag sm">寝室长</span>
        </span>
        <span class="sub">{{ member.college }}<template v-if="member.class_name"> · {{ member.class_name }} 班</template> · {{ member.phone }}</span>
      </span>
    </span>
    <span class="pos">{{ member.position_label }}</span>
  </div>
</template>

<style scoped>
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid var(--hair);
}
.row:last-child {
  border-bottom: none;
}
.left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.idx {
  font-size: 13px;
  width: 14px;
  color: var(--mute);
  flex: none;
}
.avatar {
  width: 32px;
  height: 32px;
  font-size: 12px;
}
.who {
  min-width: 0;
}
.nameline {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  flex-wrap: wrap;
}
.me {
  font-size: 10px;
  color: var(--mute);
  font-weight: 600;
}
.sub {
  display: block;
  font-size: 9.5px;
  color: var(--mute);
  margin-top: 2px;
  letter-spacing: 0.02em;
}
.pos {
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--mute);
  font-weight: 700;
  flex: none;
}
</style>
