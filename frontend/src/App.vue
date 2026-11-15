<script setup lang="ts">
import IconSprite from '@/components/base/IconSprite.vue'
import ToastHost from '@/components/feedback/ToastHost.vue'
</script>

<template>
  <IconSprite />
  <RouterView v-slot="{ Component }">
    <Transition name="page" mode="out-in">
      <KeepAlive :include="['RepairList', 'PaymentCenter']">
        <component :is="Component" />
      </KeepAlive>
    </Transition>
  </RouterView>
  <ToastHost />
</template>
