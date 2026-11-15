<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BButton from '@/components/base/BButton.vue'
import BIcon from '@/components/base/BIcon.vue'
import BTag from '@/components/base/BTag.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { paymentApi } from '@/api/payment'
import { errText, isBizError } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { fmtMoney, uuid } from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useBadgeStore } from '@/stores/badge'
import { billDirty } from '@/utils/dirty'

const props = defineProps<{ id: string }>()
const router = useRouter()
const ui = useUiStore()
const badge = useBadgeStore()

const { data, loading, error, refresh } = useAsyncData(`bill:${props.id}`, () => paymentApi.detail(props.id))
const channel = ref('wechat')
const paying = ref(false)

const channels = computed(() => data.value?.channel_options || [])
const paid = computed(() => data.value?.status === 'paid')
const payable = computed(() => !!data.value?.payable)

onMounted(refresh)

function pick(value: string, disabled: boolean) {
  if (disabled) {
    ui.toast('该渠道当前不可用', 'red')
    return
  }
  channel.value = value
}

async function pay() {
  if (!data.value || paying.value) return
  paying.value = true
  try {
    const res = await paymentApi.create([data.value.id], channel.value, `pay-${Date.now()}-${uuid()}`)
    try {
      await paymentApi.mockPay(res.txn_no, true)
    } catch {
      // 真实网关在此唤起支付
    }
    billDirty.value = true
    badge.refresh(true)
    await router.push(`/payment/result/${res.txn_no}`)
  } catch (e) {
    if (isBizError(e) && (e.code === 4001 || e.code === 4002)) {
      ui.toast(e.message, 'red')
      await refresh(true)
    } else {
      ui.toast(errText(e, '下单失败，请稍后重试'), 'red')
    }
  } finally {
    paying.value = false
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
          <span class="no">账单 NO. {{ data.bill_no }}</span>
          <BTag :text="data.status_label" :tone="paid ? 'gray' : data.overdue_days > 0 ? 'red' : 'ink'" />
        </div>

        <h1 class="big title">{{ data.title }}</h1>
        <p class="mini sub">{{ data.period }}<template v-if="data.room_text"> · {{ data.room_text }}</template></p>

        <div class="amount num-lg">{{ fmtMoney(data.total) }}</div>
        <p v-if="Number(data.late_fee) > 0" class="mini late">含滞纳金 {{ fmtMoney(data.late_fee) }}（逾期 {{ data.overdue_days }} 天）</p>

        <div class="sec" :style="{ marginBottom: '4px' }"><span class="l"><span class="h-cn">费用明细</span><span class="h-en">DETAIL</span></span></div>
        <div class="rowline" v-for="(it, i) in data.detail.items" :key="i">
          <span class="mute itemlabel">{{ it.label }}</span>
          <span class="num-lg itemval" :class="{ red: it.label.includes('超额') || it.label.includes('滞纳') }">
            {{ it.value }}<template v-if="it.unit"> {{ it.unit }}</template>
          </span>
        </div>
        <div v-if="data.detail.remark" class="rowline">
          <span class="mute itemlabel">说明</span>
          <span class="remark">{{ data.detail.remark }}</span>
        </div>
        <div class="rowline">
          <span class="mute itemlabel">截止日期</span>
          <span class="v">{{ data.due_text || data.due_date }}</span>
        </div>

        <template v-if="!paid && payable">
          <div class="sec" :style="{ marginBottom: '6px' }"><span class="l"><span class="h-cn">支付方式</span><span class="h-en">CHANNEL</span></span></div>
          <button
            v-for="c in channels"
            :key="c.value"
            type="button"
            class="channel"
            :class="{ on: channel === c.value, off: c.disabled }"
            @click="pick(c.value, c.disabled)"
          >
            <span class="ck" :class="{ on: channel === c.value }" />
            <span class="cname">{{ c.label }}</span>
            <span v-if="c.hint === '推荐'" class="tag red sm">推荐</span>
            <span v-else-if="c.hint" class="mini chint">{{ c.hint }}</span>
          </button>

          <div class="notice paynotice">请在 15 分钟内完成支付，超时订单将自动关闭，需重新下单。</div>

          <div class="spacer" />
          <BButton :loading="paying" @click="pay">立即支付 {{ fmtMoney(data.total) }}</BButton>
          <p class="hint">由学校财务处统一监管 · 请勿向个人转账</p>
        </template>

        <template v-else-if="paid">
          <div class="panel paidbox">
            <BIcon name="check" :size="20" class="ok" />
            <div>
              <b>该账单已缴清</b>
              <div class="mini" style="text-transform: none; margin-top: 4px">支付时间 {{ data.paid_at?.replace('T', ' ').slice(0, 19) || '—' }}</div>
            </div>
          </div>
          <BButton variant="ghost" @click="router.push('/payment/records')">查看电子票据 →</BButton>
        </template>

        <div v-else class="notice unpayable">该账单当前不可支付，如有疑问请联系宿管中心 0510-8818 6112。</div>
      </template>
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
}
.title {
  font-size: 28px;
  margin-top: 10px;
}
.sub {
  margin-top: 4px;
  text-transform: none;
  letter-spacing: 0.03em;
}
.amount {
  font-size: 40px;
  margin-top: 12px;
}
.late {
  margin-top: 4px;
  color: var(--red);
  text-transform: none;
}
.itemlabel {
  font-size: 11.5px;
}
.itemval {
  font-size: 15px;
}
.remark {
  font-size: 11px;
  text-align: right;
  max-width: 62%;
  line-height: 1.6;
}
.v {
  font-size: 12px;
  font-weight: 700;
}
.channel {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 13px 0;
  border-bottom: 1px solid var(--hair);
  text-align: left;
}
.channel.on {
  font-weight: 800;
}
.channel.off {
  opacity: 0.45;
}
.cname {
  font-size: 12.5px;
  font-weight: 700;
}
.chint {
  margin-left: auto;
  text-transform: none;
  letter-spacing: 0.02em;
}
.paynotice {
  margin-top: 14px;
  font-size: 10px;
}
.hint {
  font-size: 9px;
  color: var(--mute);
  text-align: center;
  margin-top: 10px;
}
.paidbox {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 14px;
  margin-top: 16px;
  border: 1px solid var(--hair);
  font-size: 12px;
}
.ok {
  color: var(--red);
  flex: none;
}
.unpayable {
  margin-top: 16px;
  font-size: 10.5px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}
</style>
