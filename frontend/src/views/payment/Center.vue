<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BillRow from '@/components/data/BillRow.vue'
import BButton from '@/components/base/BButton.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { paymentApi } from '@/api/payment'
import { errText, isBizError } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { billDirty } from '@/utils/dirty'
import { fmtMoney, sumMoney, uuid } from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useBadgeStore } from '@/stores/badge'
import type { Bill } from '@/api/types'

defineOptions({ name: 'PaymentCenter' })

const router = useRouter()
const ui = useUiStore()
const badge = useBadgeStore()

const TABS = [
  { value: 'unpaid', label: '待缴' },
  { value: 'paid', label: '已缴' },
  { value: 'overdue', label: '已逾期' },
]
const tab = ref('unpaid')
const selected = ref<number[]>([])
const paying = ref(false)

const summary = useAsyncData('bills:summary', paymentApi.summary)
const list = useAsyncData<{ items: Bill[]; total: number }>(
  'bills:list:unpaid',
  () => paymentApi.list({ status: tab.value, page_size: 50 }),
)

const bills = computed(() => list.data.value?.items || [])
const selectedBills = computed(() => bills.value.filter((b) => selected.value.includes(b.id)))
const totalAmount = computed(() => sumMoney(selectedBills.value.map((b) => b.total)))
const hasPenalty = computed(() => selectedBills.value.some((b) => !b.mergeable))
const canPay = computed(() => selected.value.length > 0 && !hasPenalty.value && !paying.value)

const counts = computed(() => ({
  unpaid: summary.data.value?.unpaid_count ?? 0,
  paid: summary.data.value?.paid_count ?? 0,
  overdue: summary.data.value?.overdue_count ?? 0,
}))

async function load(reset = false) {
  if (reset) selected.value = []
  await Promise.all([list.refresh(), summary.refresh()])
}

watch(tab, () => {
  selected.value = []
  void list.refresh()
})

onMounted(load)
onActivated(() => {
  if (billDirty.value) {
    billDirty.value = false
    void load()
  }
})

function toggle(id: number) {
  const bill = bills.value.find((b) => b.id === id)
  if (!bill?.mergeable) {
    ui.toast('罚金账单不可与其他账单合并支付', 'red')
    return
  }
  selected.value = selected.value.includes(id) ? selected.value.filter((i) => i !== id) : [...selected.value, id]
}

async function pay() {
  if (!canPay.value) return
  paying.value = true
  try {
    const res = await paymentApi.create(selected.value, 'wechat', `pay-${Date.now()}-${uuid()}`)
    // Mock 网关：直接标记支付成功，再由结果页服务端主动查单确认
    try {
      await paymentApi.mockPay(res.txn_no, true)
    } catch {
      // 真实网关由用户唤起支付，无需本地标记
    }
    billDirty.value = true
    badge.refresh(true)
    await router.push(`/payment/result/${res.txn_no}`)
  } catch (e) {
    if (isBizError(e) && (e.code === 4001 || e.code === 4002)) {
      ui.toast(e.message, 'red')
      await load()
    } else {
      ui.toast(errText(e, '下单失败，请稍后重试'), 'red')
    }
  } finally {
    paying.value = false
  }
}
</script>

<template>
  <AppShell tab="payment">
    <div class="page">
      <div class="k-brand">PAYMENT</div>
      <h1 class="big title">缴费中心</h1>

      <div class="sumline">
        <button
          v-for="t in TABS"
          :key="t.value"
          type="button"
          class="stab"
          :class="{ on: tab === t.value, overdue: t.value === 'overdue' && counts.overdue > 0 }"
          @click="tab = t.value"
        >
          {{ t.label }} {{ counts[t.value as 'unpaid' | 'paid' | 'overdue'] }}
        </button>
        <span class="mini semester">{{ summary.data.value?.semester_label || '本学期' }} {{ fmtMoney(summary.data.value?.semester_total ?? 0) }}</span>
      </div>

      <div class="sec" :style="{ marginBottom: '4px' }">
        <span class="l"><span class="h-cn">账单清单</span><span class="h-en">BILLS</span></span>
        <span class="all">多选合并支付</span>
      </div>

      <div class="cols">
        <div class="col-bills">
          <SkeletonList v-if="list.loading.value && !bills.length" :rows="3" variant="row" />
          <ErrorRetry v-else-if="list.error.value" :message="list.error.value" @retry="load()" />
          <EmptyState
            v-else-if="!bills.length"
            :title="tab === 'unpaid' ? '暂无待缴账单' : tab === 'paid' ? '暂无已缴记录' : '没有逾期账单'"
            desc="账单生成后会通过消息通知你"
            icon="card"
          />
          <template v-else>
            <BillRow
              v-for="(b, i) in bills"
              :key="b.id"
              :bill="b"
              :first="i === 0"
              :selectable="tab === 'unpaid'"
              :checked="selected.includes(b.id)"
              @toggle="toggle(b.id)"
              @open="router.push(`/payment/bill/${b.id}`)"
            />
          </template>
        </div>

        <aside class="col-side">
          <div class="notice tip">
            缴费须知 · 账单由学校财务处统一生成，逾期每日按 0.05% 计收滞纳金（封顶 30%）；罚金账单需单独缴纳。
          </div>

          <button type="button" class="btn ghost sm records" @click="router.push('/payment/records')">缴费记录与电子票据 →</button>
        </aside>
      </div>

      <div class="spacer" />

      <div v-if="tab === 'unpaid' && bills.length" class="paybar">
        <div class="payleft">
          <span class="mini">已选 {{ selected.length }} 笔合计</span>
          <span class="num-lg payamt">{{ fmtMoney(totalAmount) }}</span>
        </div>
        <BButton :disabled="!canPay" :loading="paying" class="paybtn" @click="pay">合并支付</BButton>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.title {
  font-size: 28px;
  margin-top: 2px;
}
.sumline {
  display: flex;
  gap: 16px;
  align-items: baseline;
  margin-top: 16px;
  font-size: 12px;
  font-weight: 800;
}
.stab {
  font-size: 12px;
  font-weight: 800;
  color: var(--mute);
  padding-bottom: 5px;
  border-bottom: 2.5px solid transparent;
}
.stab.on {
  color: var(--red);
  border-bottom-color: var(--red);
}
.stab.overdue:not(.on) {
  color: var(--red);
  opacity: 0.65;
}
.semester {
  margin-left: auto;
  text-transform: none;
  letter-spacing: 0.02em;
}
.tip {
  margin-top: 16px;
  font-size: 10px;
}
.records {
  margin-top: 14px;
}
.paybar {
  position: sticky;
  bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom));
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-top: var(--line) solid var(--ink);
  padding: 10px 0 calc(6px + env(safe-area-inset-bottom));
  margin-top: 8px;
}
.payleft {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.payamt {
  font-size: 20px;
}
.paybtn {
  width: 130px;
  flex: none;
  margin-top: 0;
  min-height: 44px;
  letter-spacing: 0.14em;
}

/* ---------- 桌面：账单左栏 + 须知侧栏 ---------- */
@media (min-width: 1024px) {
  .title {
    font-size: 34px;
  }

  .sumline {
    margin-top: 18px;
  }

  .stab {
    font-size: 13px;
    padding: 9px 0;
  }

  .cols {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
    gap: 40px;
    align-items: start;
  }

  .col-side {
    border-left: 1px solid var(--hair);
    padding-left: 32px;
    margin-top: 8px;
  }

  .col-bills :deep(.bill) {
    padding: 18px;
    border-left: 1px solid var(--hair);
    border-right: 1px solid var(--hair);
  }

  .col-bills :deep(.bill:first-child) {
    border-top: var(--line) solid var(--ink);
  }

  .col-bills :deep(.bill:last-child) {
    border-bottom: 1px solid var(--hair);
  }

  .col-bills :deep(.title) {
    font-size: 15px;
  }

  .tip {
    margin-top: 0;
    font-size: 12px;
    line-height: 1.8;
  }

  .records {
    margin-top: 16px;
    width: 100%;
  }

  .paybar {
    margin-top: 18px;
    padding: 14px 0 6px;
  }

  .payamt {
    font-size: 26px;
  }

  .paybtn {
    min-width: 190px;
  }
}
</style>
