<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BButton from '@/components/base/BButton.vue'
import BField from '@/components/base/BField.vue'
import BSheet from '@/components/base/BSheet.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import { paymentApi } from '@/api/payment'
import { errText } from '@/api/client'
import { saveBlob } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import { fmtMoney } from '@/utils/format'
import { isEmail } from '@/utils/validate'
import type { BillRecords } from '@/api/types'

const ui = useUiStore()
const { data, loading, error, refresh } = useAsyncData<BillRecords>('bills:records', () => paymentApi.records())

const exportOpen = ref(false)
const receiptOpen = ref(false)
const target = ref<{ id: number; title: string } | null>(null)
const email = ref('')
const applying = ref(false)
const exporting = ref(false)
const sentMap = ref<Record<number, string>>({})

const groups = computed(() => data.value?.groups || [])

function amountText(v: string): string {
  const n = Number(v)
  return `${n < 0 ? '−' : ''}${fmtMoney(Math.abs(n))}`
}

function openReceipt(item: { id: number; title: string }) {
  target.value = item
  email.value = ''
  receiptOpen.value = true
}

async function applyReceipt() {
  if (!target.value) return
  if (email.value && !isEmail(email.value)) {
    ui.toast('邮箱格式有误', 'red')
    return
  }
  applying.value = true
  try {
    const res = await paymentApi.applyReceipt(target.value.id, email.value.trim() || undefined)
    sentMap.value = { ...sentMap.value, [target.value.id]: 'applying' }
    receiptOpen.value = false
    ui.toast('票据申请已提交，将发送至邮箱')
    await refresh(true)
  } catch (e) {
    ui.toast(errText(e, '申请失败'), 'red')
  } finally {
    applying.value = false
  }
}

async function download(item: { id: number; receipt_file: string | null; receipt_id: number | null }) {
  if (!item.receipt_id) return
  try {
    const { blob, filename } = await paymentApi.receiptFile(item.receipt_id)
    saveBlob(blob, filename)
  } catch (e) {
    ui.toast(errText(e, '下载失败'), 'red')
  }
}

async function exportCsv() {
  exporting.value = true
  try {
    const { blob, filename } = await paymentApi.exportRecords()
    saveBlob(blob, filename)
    exportOpen.value = false
    ui.toast('对账单已导出')
  } catch (e) {
    ui.toast(errText(e, '导出失败'), 'red')
  } finally {
    exporting.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="RECORDS" title="缴费记录与票据" back @back="$router.back()" />

      <div class="filterbar">
        <span class="mini year">{{ data?.year || '全部学年' }} ▾</span>
        <span class="mini">全部类型 ▾</span>
        <button type="button" class="btn-text export" @click="exportOpen = true">导出对账单</button>
      </div>

      <SkeletonList v-if="loading && !data" :rows="4" variant="row" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />
      <EmptyState v-else-if="!groups.length" title="暂无缴费记录" desc="缴费成功后将在此生成流水与票据" icon="card" />

      <template v-else>
        <section v-for="g in groups" :key="g.month">
          <div class="sec" :style="{ marginBottom: '4px' }">
            <span class="l"><span class="h-cn">{{ g.label }}</span><span class="h-en">{{ g.en }}</span></span>
            <span class="mini gtotal">{{ amountText('-' + g.total) }}</span>
          </div>
          <div v-for="it in g.items" :key="it.id" class="rowline">
            <div class="linfo">
              <b class="ltitle">{{ it.title }}</b>
              <span class="mini lsub">{{ it.sub }}</span>
            </div>
            <div class="right">
              <span class="num-lg amt">{{ amountText(it.amount) }}</span>
              <button
                v-if="it.receipt_status === 'sent' || sentMap[it.id] === 'sent'"
                type="button"
                class="mini rstatus"
                @click="download(it)"
              >
                票据已发邮箱
              </button>
              <span v-else-if="it.receipt_status === 'pending' || sentMap[it.id]"
                class="mini rstatus processing">开票中</span>
              <button v-else-if="it.can_apply_receipt" type="button" class="mini rstatus red" @click="openReceipt(it)">
                申请票据 →
              </button>
            </div>
          </div>
        </section>

        <template v-if="data?.overdue?.length">
          <div class="sec"><span class="l"><span class="h-cn">逾期留痕</span><span class="h-en">OVERDUE</span></span></div>
          <div v-for="(o, i) in data.overdue" :key="i" class="notice overdue">{{ o.text }}</div>
        </template>

        <p class="yeartotal">本学年累计缴费 <b class="num-lg">{{ fmtMoney(data?.year_total ?? 0) }}</b></p>
      </template>

      <BSheet v-model="receiptOpen" title="申请电子票据">
        <p class="sheetdesc">票据为电子版 PDF，开具后发送至所填邮箱，也可在记录中直接下载。</p>
        <BField v-model="email" label="接收邮箱" placeholder="name@example.edu" inputmode="email" />
        <template #footer>
          <BButton :loading="applying" @click="applyReceipt">提交申请</BButton>
        </template>
      </BSheet>

      <BSheet v-model="exportOpen" title="导出对账单">
        <p class="sheetdesc">导出当前学年全部已缴流水（CSV，Excel 可直接打开，含逾期留痕）。</p>
        <template #footer>
          <BButton :loading="exporting" @click="exportCsv">确认导出</BButton>
        </template>
      </BSheet>
    </div>
  </AppShell>
</template>

<style scoped>
.filterbar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
}
.year,
.filterbar .mini {
  text-transform: none;
  letter-spacing: 0.02em;
}
.export {
  margin-left: auto;
  letter-spacing: 0.14em;
  font-size: 9px;
}
.gtotal {
  text-transform: none;
}
.linfo {
  min-width: 0;
}
.ltitle {
  font-size: 12.5px;
}
.lsub {
  display: block;
  margin-top: 2px;
  text-transform: none;
  letter-spacing: 0.02em;
}
.right {
  text-align: right;
  flex: none;
}
.amt {
  font-size: 15px;
}
.rstatus {
  display: block;
  margin-top: 2px;
  text-transform: none;
  letter-spacing: 0.04em;
  margin-left: auto;
}
.rstatus.processing {
  color: var(--mute);
}
.overdue {
  margin-bottom: 8px;
  font-size: 10.5px;
  line-height: 1.7;
}
.yeartotal {
  margin-top: 20px;
  font-size: 11px;
  color: var(--mute);
  text-align: center;
}
.yeartotal b {
  color: var(--ink);
  font-size: 15px;
  margin-left: 4px;
}
.sheetdesc {
  font-size: 11px;
  color: var(--mute);
  line-height: 1.7;
  margin: 8px 0 12px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}

/* ---------- 宽屏：列表自动多列（跨列元素保持整行） ---------- */
@media (min-width: 1100px) {
  .page {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    column-gap: clamp(24px, 2.6vw, 52px);
    align-content: start;
  }

  .page > * {
    min-width: 0;
  }

  .page > .filterbar,
  .page > .head,
  .page > .sec,
  .page > .title,
  .page > .k-brand,
  .page > .sub,
  .page > .pinned,
  .page > .rules,
  .page > .statgrid,
  .page > .spacer,
  .page > .nofaq,
  .page > .notice,
  .page > .tip,
  .page > .actions,
  .page > .groups,
  .page > .subline {
    grid-column: 1 / -1;
  }
}
</style>
