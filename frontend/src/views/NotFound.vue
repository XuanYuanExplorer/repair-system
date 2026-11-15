<script setup lang="ts">
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BButton from '@/components/base/BButton.vue'

const router = useRouter()
</script>

<template>
  <AppShell>
    <div class="page nf">
      <div class="k-brand">404 / NOT FOUND</div>
      <h1 class="big code">页面<br />不存在</h1>
      <p class="mini desc">链接可能已失效，或该内容已下线</p>
      <div class="spacer" />
      <BButton @click="router.replace('/')">返回服务大厅</BButton>
      <BButton variant="ghost" class="mt" @click="router.back()">返回上一页</BButton>
    </div>
  </AppShell>
</template>

<style scoped>
.nf {
  min-height: 100%;
}
.code {
  font-size: 40px;
  line-height: 1.1;
  margin-top: 12px;
}
.desc {
  margin-top: 8px;
  text-transform: none;
  letter-spacing: 0.04em;
}
.mt {
  margin-top: 10px;
}
</style>
