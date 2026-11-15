<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BSwitch from '@/components/base/BSwitch.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import { messageApi } from '@/api/message'
import { errText } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import { useBadgeStore } from '@/stores/badge'
import { MESSAGE_TYPE } from '@/utils/dict'
import type { MessageItem, MessagePreferences } from '@/api/types'

const router = useRouter()
const ui = useUiStore()
const badge = useBadgeStore()

const list = useAsyncData('messages', () => messageApi.list({ page_size: 50 }))
const prefs = ref<MessagePreferences | null>(null)
const readAllOpen = ref(false)
const prefsOpen = ref(false)
const saving = ref(false)

const groups = computed(() => list.data.value?.groups || [])
const unreadTotal = computed(() => list.data.value?.unread_total ?? 0)

list.refresh().then(async () => {
  try {
    prefs.value = await messageApi.preferences()
  } catch {
    // 偏好读取失败不影响列表
  }
})

async function open(m: MessageItem) {
  if (!m.is_read) {
    try {
      await messageApi.readOne(m.id)
      m.is_read = true
      badge.decUnread()
      await list.refresh(true)
    } catch {
      // 忽略
    }
  }
  if (m.biz_type === 'repair_order' && m.biz_id) router.push(`/repair/${m.biz_id}`)
  else if (m.biz_type === 'bill' && m.biz_id) router.push(`/payment/bill/${m.biz_id}`)
  else if (m.biz_type === 'notice') router.push('/dorm/notice')
  else if (m.biz_type === 'payment') router.push('/payment/records')
}

async function readAll() {
  try {
    await messageApi.readAll()
    readAllOpen.value = false
    badge.clearUnread()
    ui.toast('已全部标记为已读')
    await list.refresh(true)
  } catch (e) {
    ui.toast(errText(e, '操作失败'), 'red')
  }
}

async function togglePref(key: 'sms' | 'wechat', value: boolean) {
  if (!prefs.value) return
  const snapshot = { ...prefs.value }
  const next: MessagePreferences = {
    ...prefs.value,
    sms_on: key === 'sms' ? value : prefs.value.sms_on,
    wechat_on: key === 'wechat' ? value : prefs.value.wechat_on,
  }
  prefs.value = next
  saving.value = true
  try {
    await messageApi.savePreferences({
      sms_types: next.sms_on ? next.sms_types : [],
      wechat_types: next.wechat_on ? next.wechat_types : [],
    })
    ui.toast('推送设置已保存')
  } catch (e) {
    prefs.value = snapshot
    ui.toast(errText(e, '保存失败，已恢复原设置'), 'red')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="topbar">
        <button type="button" class="back" aria-label="返回" @click="$router.back()">←</button>
        <h1 class="big title">消息中心</h1>
        <button type="button" class="readall" :disabled="!unreadTotal" @click="readAllOpen = true">全部已读</button>
      </div>
      <p class="mini sub">MESSAGES · 按业务类型分组 · 未读 {{ unreadTotal }}</p>

      <SkeletonList v-if="list.loading.value && !groups.length" :rows="4" variant="row" />
      <ErrorRetry v-else-if="list.error.value" :message="list.error.value" @retry="list.refresh()" />
      <EmptyState v-else-if="!groups.length" title="暂无消息" desc="工单、账单与公告提醒会出现在这里" icon="bell" />

      <template v-else>
        <div class="groups">
        <section v-for="g in groups" :key="g.type">
          <div class="sec">
            <span class="l"><span class="h-cn">{{ g.label }}</span><span class="h-en">{{ MESSAGE_TYPE[g.type]?.en || g.type.toUpperCase() }}</span></span>
            <span v-if="g.unread" class="badge">{{ g.unread }}</span>
            <span v-else class="mini total">{{ g.total }}</span>
          </div>
          <button
            v-for="m in g.items"
            :key="m.id"
            type="button"
            class="msg"
            :class="{ unread: !m.is_read }"
            @click="open(m)"
          >
            <span class="mtitle" :class="{ red: !m.is_read && g.type === 'bill' }">{{ m.title }}</span>
            <span class="mcontent">{{ m.content }}</span>
            <span class="mini mtime">{{ m.time_text.slice(6) }}</span>
          </button>
        </section>
        </div>

        <button type="button" class="prefbtn" @click="prefsOpen = true">
          推送设置 · PUSH <span class="mini">{{ prefs ? `${prefs.sms_on ? '短信' : ''}${prefs.wechat_on ? ' / 微信' : ''} 已开启` : '' }}</span>
        </button>
      </template>

      <BSheet v-model="readAllOpen" title="全部标记已读">
        <p class="sheetdesc">将把全部 {{ unreadTotal }} 条未读消息标记为已读，此操作不可撤销。</p>
        <template #footer>
          <BButton @click="readAll">确认全部已读</BButton>
        </template>
      </BSheet>

      <BSheet v-model="prefsOpen" title="推送设置">
        <p class="sheetdesc">{{ prefs?.note || '仅限账单 / 查寝类' }}</p>
        <div class="prefrow">
          <span>
            短信同步
            <span class="mini">账期、逾期、查寝结果</span>
          </span>
          <BSwitch :model-value="!!prefs?.sms_on" :disabled="saving" label="短信同步" @update:model-value="(v) => togglePref('sms', v)" />
        </div>
        <div class="prefrow">
          <span>
            微信推送
            <span class="mini">需关注学校企业微信</span>
          </span>
          <BSwitch :model-value="!!prefs?.wechat_on" :disabled="saving" label="微信推送" @update:model-value="(v) => togglePref('wechat', v)" />
        </div>
        <template #footer>
          <BButton variant="ghost" @click="prefsOpen = false">完成</BButton>
        </template>
      </BSheet>
    </div>
  </AppShell>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.back {
  font-size: 15px;
  padding: 2px 4px 2px 0;
}
.title {
  font-size: 28px;
  flex: 1;
}
.readall {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--red);
}
.readall:disabled {
  color: var(--mute);
  opacity: 0.5;
}
.sub {
  margin-top: 6px;
  text-transform: none;
  letter-spacing: 0.04em;
}
.msg {
  display: block;
  width: 100%;
  text-align: left;
  padding: 11px 0 11px 8px;
  border-bottom: 1px solid var(--hair);
  position: relative;
}
.msg.unread::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--red);
}
.mtitle {
  display: block;
  font-size: 12.5px;
  font-weight: 700;
}
.mcontent {
  display: block;
  font-size: 10.5px;
  color: var(--mute);
  margin-top: 3px;
  line-height: 1.6;
}
.mtime {
  position: absolute;
  right: 0;
  bottom: 11px;
}
.total {
  text-transform: none;
}
.prefbtn {
  margin-top: 18px;
  width: 100%;
  text-align: left;
  border-top: var(--line) solid var(--ink);
  padding-top: 11px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  display: flex;
  justify-content: space-between;
}
.prefbtn .mini {
  text-transform: none;
  letter-spacing: 0.02em;
  font-weight: 600;
}
.sheetdesc {
  font-size: 11px;
  color: var(--mute);
  line-height: 1.7;
  margin: 8px 0 12px;
}
.prefrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--hair);
  font-size: 12px;
  font-weight: 700;
}
.prefrow .mini {
  display: block;
  margin-top: 3px;
  text-transform: none;
  letter-spacing: 0.02em;
  font-weight: 500;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}

/* ---------- 宽屏：消息分组多列 ---------- */
@media (min-width: 1100px) {
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
    gap: 0 clamp(28px, 3vw, 56px);
    align-items: start;
  }

  .msg {
    padding: clamp(12px, 1vw, 16px) 12px;
  }

  .mtitle {
    font-size: clamp(14px, 0.9vw, 17px);
  }

  .mcontent {
    font-size: clamp(12px, 0.78vw, 14px);
  }

  .prefbtn {
    max-width: 520px;
  }
}
</style>
