<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BIcon from '@/components/base/BIcon.vue'
import BButton from '@/components/base/BButton.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { paymentApi } from '@/api/payment'
import { errText } from '@/api/client'
import { usePolling } from '@/composables/usePolling'
import { useUiStore } from '@/stores/ui'
import { useBadgeStore } from '@/stores/badge'
import { fmtMoney } from '@/utils/format'
import type { TxnResult } from '@/api/types'

const props = defineProps<{ txnNo: string }>()
const router = useRouter()
const ui = useUiStore()
const badge = useBadgeStore()

const txn = ref<TxnResult | null>(null)
const loading = ref(true)
const error = ref('')
const timedOut = ref(false)

const status = computed(() => txn.value?.status || 'processing')
const isTerminal = computed(() => ['success', 'failed', 'closed'].includes(status.value))

/** 进入即主动查单，不读 URL 上的 status 参数（可被伪造） */
async function fetchStatus(): Promise<boolean> {
  try {
    const res = await paymentApi.txn(props.txnNo)
    txn.value = res
    error.value = ''
    if (res.status === 'success') badge.refresh(true)
    return ['success', 'failed', 'closed'].includes(res.status)
  } catch (e) {
    error.value = errText(e, '查询订单状态失败')
    return false
  } finally {
    loading.value = false
  }
}

const polling = usePolling(fetchStatus, { interval: 2000, max: 15 })

onMounted(async () => {
  const done = await fetchStatus()
  if (!done) polling.start()
  setTimeout(() => {
    if (!isTerminal.value) timedOut.value = true
  }, 32_000)
})

async function refreshManually() {
  loading.value = true
  const done = await fetchStatus()
  if (done) polling.stop()
}

function rebill() {
  const first = txn.value?.bills?.[0]
  if (first) router.replace(`/payment/bill/${first.id}`)
  else router.replace('/payment')
}

const paidText = computed(() => {
  const raw = txn.value?.paid_at
  return raw ? raw.replace('T', ' ').slice(0, 19) : '—'
})
</script>

<template>
  <AppShell>
    <div class="page center">
      <div class="k-brand left">PAYMENT RESULT</div>

      <SkeletonList v-if="loading && !txn" :rows="3" variant="detail" />
      <ErrorRetry v-else-if="error && !txn" :message="error" @retry="refreshManually" />

      <template v-else-if="txn">
        <!-- 成功 -->
        <template v-if="status === 'success'">
          <BIcon name="check" :size="60" :stroke="1.2" class="bigicon ok" />
          <h1 class="big stitle">支付成功</h1>
          <p class="mini subline">SUCCESS · 服务端订单状态已主动核对，防掉单</p>
          <div class="num-lg amount">{{ fmtMoney(txn.amount) }}</div>
          <div class="details">
            <div class="rowline"><span class="k">订单号</span><span class="v num-lg">{{ txn.txn_no }}</span></div>
            <div class="rowline"><span class="k">到账时间</span><span class="v">{{ paidText }}</span></div>
            <div class="rowline"><span class="k">支付方式</span><span class="v">{{ txn.channel_label }}</span></div>
            <div class="rowline"><span class="k">关联账单</span><span class="v">{{ txn.bills.map((b) => b.title).join('、') || '—' }}</span></div>
          </div>
          <BButton @click="router.replace('/')">返回首页</BButton>
          <button type="button" class="linkbtn" @click="router.push('/payment/records')">查看电子票据 →</button>
        </template>

        <!-- 处理中 -->
        <template v-else-if="status === 'processing'">
          <BIcon name="clock" :size="56" :stroke="1.2" class="bigicon" />
          <h1 class="big stitle">支付处理中</h1>
          <p class="mini subline">银行处理中，预计 1 分钟内完成</p>
          <div class="num-lg amount">{{ fmtMoney(txn.amount) }}</div>
          <div class="details">
            <div class="rowline"><span class="k">订单号</span><span class="v num-lg">{{ txn.txn_no }}</span></div>
            <div class="rowline"><span class="k">支付方式</span><span class="v">{{ txn.channel_label }}</span></div>
            <div class="rowline"><span class="k">关联账单</span><span class="v">{{ txn.bills.map((b) => b.title).join('、') || '—' }}</span></div>
          </div>
          <p v-if="timedOut" class="notice waiting">处理中，稍后可在「缴费记录」查看结果。</p>
          <BButton variant="ghost" :loading="loading" @click="refreshManually">刷新状态</BButton>
          <BButton variant="ghost" class="mt" @click="router.replace('/')">返回首页</BButton>
        </template>

        <!-- 失败 / 关闭 -->
        <template v-else>
          <BIcon name="alert" :size="56" :stroke="1.2" class="bigicon fail" />
          <h1 class="big stitle fail">支付失败</h1>
          <p class="mini subline fail">{{ txn.fail_reason || '订单已关闭，请重新发起支付' }}</p>
          <div class="num-lg amount">{{ fmtMoney(txn.amount) }}</div>
          <div class="details">
            <div class="rowline"><span class="k">订单号</span><span class="v num-lg">{{ txn.txn_no }}</span></div>
            <div class="rowline"><span class="k">关联账单</span><span class="v">{{ txn.bills.map((b) => b.title).join('、') || '—' }}</span></div>
          </div>
          <BButton @click="rebill">重新支付</BButton>
          <button type="button" class="linkbtn" @click="router.push('/help')">联系客服 →</button>
        </template>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.center {
  text-align: center;
}
.left {
  text-align: left;
}
.bigicon {
  margin: 26px auto 0;
  display: block;
  color: var(--ink);
}
.bigicon.ok {
  color: var(--ink);
}
.bigicon.fail {
  color: var(--red);
}
.stitle {
  font-size: 30px;
  margin-top: 16px;
}
.stitle.fail {
  color: var(--red);
}
.subline {
  margin-top: 6px;
  text-transform: none;
  letter-spacing: 0.04em;
  line-height: 1.7;
}
.subline.fail {
  color: var(--red);
}
.amount {
  font-size: 46px;
  margin-top: 18px;
}
.details {
  border-top: var(--line) solid var(--ink);
  margin-top: 22px;
  text-align: left;
}
.k {
  font-size: 11.5px;
  color: var(--mute);
}
.v {
  font-size: 12px;
  font-weight: 700;
  text-align: right;
  word-break: break-all;
}
.linkbtn {
  margin-top: 14px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
  border-bottom: var(--line) solid var(--ink);
  padding-bottom: 2px;
}
.waiting {
  margin: 14px 0;
  font-size: 10.5px;
  text-align: left;
}
.mt {
  margin-top: 10px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: 720px;
    width: 100%;
    margin: 0 auto;
  }
}
</style>
