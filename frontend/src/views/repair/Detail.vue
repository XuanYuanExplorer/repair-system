<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BIcon from '@/components/base/BIcon.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import BField from '@/components/base/BField.vue'
import StatusTag from '@/components/data/StatusTag.vue'
import Timeline from '@/components/data/Timeline.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { repairApi } from '@/api/repair'
import { errText, isBizError } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useCountdown } from '@/composables/useCountdown'
import { usePolling } from '@/composables/usePolling'
import { useUiStore } from '@/stores/ui'
import { repairDirty } from '@/utils/dirty'
import { copyText, familyName, fmtTime } from '@/utils/format'
import type { ChatMessage } from '@/api/types'

const props = defineProps<{ id: string }>()
const router = useRouter()
const ui = useUiStore()

const orderId = computed(() => Number(props.id))
const { data, loading, error, refresh } = useAsyncData(`repair:${props.id}`, () => repairApi.detail(orderId.value))
const urge = useCountdown(0)

const cancelOpen = ref(false)
const cancelReason = ref('')
const editOpen = ref(false)
const editDesc = ref('')
const editPhone = ref('')
const editSlot = ref('')
const chatOpen = ref(false)
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const chatBody = ref<HTMLElement | null>(null)

const status = computed(() => data.value?.status || 'pending')
const SLOT_LABEL: Record<string, string> = { '09-11': '09:00–11:00', '14-16': '14:00–16:00', '16-18': '16:00–18:00' }
const slotLabel = computed(() => SLOT_LABEL[data.value?.preferred_slot || ''] || data.value?.preferred_slot || '不限')

onMounted(async () => {
  await refresh()
  if (data.value?.urge_cooldown_sec) urge.start(data.value.urge_cooldown_sec)
})

function syncDirty() {
  repairDirty.value = true
}

async function doCopy() {
  if (!data.value) return
  const ok = await copyText(data.value.order_no)
  ui.toast(ok ? '单号已复制' : '复制失败，请手动选择')
}

async function doUrge() {
  if (!data.value || urge.active.value) return
  try {
    const res = await repairApi.urge(orderId.value)
    urge.start(res.retry_after || 300)
    ui.toast('已催单，宿管将尽快处理')
    syncDirty()
  } catch (e) {
    if (isBizError(e) && e.code === 3003) {
      urge.start(Number((e.data as { retry_after?: number } | null)?.retry_after ?? 60))
      ui.toast('催单过于频繁，请稍后再试', 'red')
    } else {
      ui.toast(errText(e), 'red')
    }
  }
}

async function doCancel() {
  try {
    await repairApi.cancel(orderId.value, cancelReason.value.trim() || undefined)
    cancelOpen.value = false
    syncDirty()
    ui.toast('工单已取消')
    await router.replace('/repair/list')
  } catch (e) {
    ui.toast(errText(e, '取消失败'), 'red')
  }
}

function openEdit() {
  if (!data.value) return
  editDesc.value = data.value.description
  editPhone.value = data.value.contact_phone
  editSlot.value = data.value.preferred_slot || ''
  editOpen.value = true
}

async function saveEdit() {
  if (!data.value) return
  try {
    await repairApi.update(orderId.value, {
      description: editDesc.value.trim(),
      contact_phone: editPhone.value,
      preferred_slot: editSlot.value || undefined,
    })
    editOpen.value = false
    syncDirty()
    ui.toast('工单已更新')
    await refresh(true)
  } catch (e) {
    if (isBizError(e) && e.code === 3001) {
      editOpen.value = false
      await refresh(true)
    }
    ui.toast(errText(e, '修改失败'), 'red')
  }
}

/* ---------------- 沟通面板 ---------------- */
async function loadMessages(afterId?: number) {
  try {
    const res = await repairApi.messages(orderId.value, afterId)
    if (afterId) {
      const known = new Set(messages.value.map((m) => m.id))
      messages.value = [...messages.value, ...res.items.filter((m) => !known.has(m.id))]
    } else {
      messages.value = res.items
    }
    await nextTick()
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  } catch {
    // 沟通失败静默，不打断主流程
  }
}

const chatPolling = usePolling(
  async () => {
    const last = messages.value[messages.value.length - 1]
    await loadMessages(last?.id)
    return !chatOpen.value
  },
  { interval: 10_000 },
)

watch(chatOpen, async (open) => {
  if (open) {
    await loadMessages()
    chatPolling.start()
  } else {
    chatPolling.stop()
  }
})

onUnmounted(() => chatPolling.stop())

async function send() {
  const content = draft.value.trim()
  if (!content || sending.value) return
  sending.value = true
  try {
    const msg = await repairApi.sendMessage(orderId.value, content)
    messages.value = [...messages.value, msg]
    draft.value = ''
    await nextTick()
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  } catch (e) {
    ui.toast(errText(e, '发送失败'), 'red')
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <SkeletonList v-if="loading && !data" :rows="4" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <div class="topbar">
          <button type="button" class="back" aria-label="返回" @click="router.back()">
            <BIcon name="chev" :size="15" /><span>返回</span>
          </button>
          <span class="no">工单 {{ data.order_no }}</span>
          <button type="button" class="copy" @click="doCopy"><BIcon name="copy" :size="12" />复制单号</button>
        </div>

        <div class="headline">
          <h1 class="big st">{{ data.status_label }}</h1>
          <StatusTag :status="data.status" size="lg" />
        </div>
        <p class="mini subline">{{ data.category_label }} · {{ data.location_desc }}</p>

        <div v-if="data.status === 'verify'" class="notice verifybar">
          师傅已完工，请核对维修结果并确认
          <button type="button" class="btn-text" @click="router.push(`/repair/${data.id}/rate`)">去确认 →</button>
        </div>

        <div class="sec"><span class="l"><span class="h-cn">工单跟踪</span><span class="h-en">TIMELINE</span></span></div>
        <Timeline :items="data.timeline" />

        <div v-if="data.worker" class="staff">
          <span class="avatar staffavatar">{{ familyName(data.worker.name) }}</span>
          <span class="staffinfo">
            <b>{{ data.worker.name }}</b>
            <span class="mini staffsub">维修师傅 · 工号 {{ data.worker.worker_no }}</span>
          </span>
          <button type="button" class="iconbtn" aria-label="沟通" @click="chatOpen = true"><BIcon name="msg" :size="16" /></button>
          <a class="iconbtn" :href="`tel:${data.worker.phone}`" aria-label="拨号"><BIcon name="phone" :size="16" /></a>
        </div>

        <div v-if="data.last_message" class="bubble">
          <div class="bubble-txt">{{ data.last_message.content }}</div>
          <div class="bubble-meta"><span>{{ data.last_message.sender_name }}</span><span>{{ fmtTime(data.last_message.at) }}</span></div>
        </div>

        <div class="sec"><span class="l"><span class="h-cn">故障描述</span><span class="h-en">DESC</span></span></div>
        <p class="desc">{{ data.description }}</p>
        <div v-if="data.media_urls.length" class="media">
          <img v-for="(u, i) in data.media_urls" :key="i" :src="u" alt="现场照片" loading="lazy" decoding="async" />
        </div>
        <div class="kv-row"><span class="mini">期望上门</span><span class="v">{{ data.preferred_date || '—' }} · {{ slotLabel }}</span></div>
        <div class="kv-row"><span class="mini">联系电话</span><span class="v">{{ data.contact_phone }}</span></div>
        <div class="kv-row"><span class="mini">本人在场</span><span class="v">{{ data.require_presence ? '是' : '否，可授权入内' }}</span></div>
        <div v-if="data.fix_note" class="kv-row"><span class="mini">完工说明</span><span class="v">{{ data.fix_note }}</span></div>

        <div class="spacer" />

        <BButton v-if="data.can_verify" @click="router.push(`/repair/${data.id}/rate`)">确认完工 / 评价</BButton>

        <div class="actions">
          <BButton v-if="data.can_urge" variant="ghost" size="sm" :disabled="urge.active.value" @click="doUrge">
            {{ urge.active.value ? `催单冷却 ${urge.text.value}` : '催单' }}
          </BButton>
          <BButton v-if="data.can_edit" variant="ghost" size="sm" @click="openEdit">修改工单</BButton>
          <BButton v-if="data.can_cancel" variant="ghost-red" size="sm" @click="cancelOpen = true">取消</BButton>
        </div>
        <p class="hint">维修开始前可修改或取消 · 超时未受理可发起催单</p>

        <!-- 取消确认 -->
        <BSheet v-model="cancelOpen" title="取消工单">
          <p class="sheetdesc">取消后需重新提交，已预约的上门时段将释放。</p>
          <textarea v-model="cancelReason" class="desc" maxlength="100" placeholder="取消原因（选填）" />
          <template #footer>
            <BButton variant="ghost-red" @click="doCancel">确认取消</BButton>
          </template>
        </BSheet>

        <!-- 修改工单 -->
        <BSheet v-model="editOpen" title="修改工单">
          <BField v-model="editDesc" label="故障描述" :maxlength="200" />
          <BField v-model="editPhone" label="联系电话" inputmode="tel" :maxlength="11" />
          <div class="slotrow">
            <span class="mini">期望时段</span>
            <select v-model="editSlot" class="mini-select">
              <option value="">不限</option>
              <option value="09-11">09:00–11:00</option>
              <option value="14-16">14:00–16:00</option>
              <option value="16-18">16:00–18:00</option>
            </select>
          </div>
          <template #footer>
            <BButton @click="saveEdit">保存修改</BButton>
          </template>
        </BSheet>

        <!-- 沟通面板 -->
        <BSheet v-model="chatOpen" title="与维修班组沟通" height="70vh">
          <div ref="chatBody" class="chat">
            <p v-if="!messages.length" class="mini chatempty">暂无沟通记录，可发送补充说明</p>
            <div v-for="m in messages" :key="m.id" class="msg" :class="{ mine: m.mine }">
              <div class="msg-txt">{{ m.content }}</div>
              <div class="msg-meta">{{ m.mine ? '我' : m.sender_name }} · {{ fmtTime(m.created_at) }}</div>
            </div>
          </div>
          <template #footer>
            <div class="chatform">
              <input v-model="draft" class="chatinput" maxlength="200" placeholder="输入消息…" @keyup.enter="send" />
              <button type="button" class="sendbtn" :disabled="!draft.trim() || sending" @click="send">发送</button>
            </div>
          </template>
        </BSheet>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 6px;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 700;
}
.back :deep(.ic) {
  transform: rotate(180deg);
}
.no {
  font-size: 9px;
  letter-spacing: 0.14em;
  color: #b9b9b7;
  font-weight: 700;
  flex: 1;
  text-align: center;
}
.copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
}
.headline {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-top: 10px;
}
.st {
  font-size: 28px;
}
.subline {
  margin-top: 6px;
  text-transform: none;
  letter-spacing: 0.03em;
}
.verifybar {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.staff {
  display: flex;
  align-items: center;
  gap: 10px;
  border: var(--line) solid var(--ink);
  padding: 12px 14px;
  margin-top: 14px;
}
.staffavatar {
  width: 36px;
  height: 36px;
  font-size: 14px;
}
.staffinfo {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.staffinfo b {
  font-size: 13px;
}
.staffsub {
  text-transform: none;
  letter-spacing: 0.02em;
}
.iconbtn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--hair);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.iconbtn:active {
  opacity: 0.6;
}
.bubble {
  background: var(--panel);
  padding: 11px 13px;
  margin-top: 10px;
}
.bubble-txt {
  font-size: 11.5px;
  line-height: 1.6;
}
.bubble-meta {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: var(--mute);
  margin-top: 6px;
  letter-spacing: 0.04em;
}
.desc {
  font-size: 11.5px;
  line-height: 1.75;
  color: #2a2a2a;
}
.media {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.media img {
  width: 58px;
  height: 58px;
  object-fit: cover;
  border: 1px solid var(--hair);
}
.kv-row .v {
  font-size: 11.5px;
  font-weight: 700;
  text-align: right;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.actions :deep(.btn) {
  flex: 1;
}
.hint {
  font-size: 9px;
  color: var(--mute);
  text-align: center;
  margin-top: 10px;
  line-height: 1.7;
}
.sheetdesc {
  font-size: 11px;
  color: var(--mute);
  line-height: 1.7;
  margin: 6px 0 10px;
}
.slotrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: var(--line) solid var(--ink);
}
.mini-select {
  width: auto;
  font-size: 11px;
  font-weight: 700;
}
.chat {
  max-height: 46vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 6px 0;
}
.chatempty {
  text-align: center;
  padding: 24px 0;
  text-transform: none;
}
.msg {
  max-width: 82%;
  align-self: flex-start;
}
.msg.mine {
  align-self: flex-end;
  text-align: right;
}
.msg-txt {
  display: inline-block;
  background: var(--panel);
  padding: 9px 12px;
  font-size: 11.5px;
  line-height: 1.6;
  text-align: left;
}
.msg.mine .msg-txt {
  background: var(--ink);
  color: #fff;
}
.msg-meta {
  font-size: 8.5px;
  color: var(--mute);
  margin-top: 3px;
  letter-spacing: 0.04em;
}
.chatform {
  display: flex;
  gap: 8px;
  align-items: center;
}
.chatinput {
  flex: 1;
  border: var(--line) solid var(--ink);
  padding: 10px 12px;
  font-size: 12px;
}
.sendbtn {
  background: var(--ink);
  color: #fff;
  padding: 10px 18px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  flex: none;
}
.sendbtn:disabled {
  opacity: 0.35;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}

/* ---------- 桌面：照片自适应多列 ---------- */
@media (min-width: 1024px) {
  .media {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 10px;
  }

  .media img {
    width: 100%;
    height: auto;
    aspect-ratio: 4 / 3;
    object-fit: cover;
  }

  .desc {
    font-size: 14px;
    line-height: 1.85;
    max-width: 72ch;
  }

  .staff {
    padding: 16px 18px;
  }

  .mono,
  .kv-row .v {
    font-size: 13px;
  }
}
</style>
