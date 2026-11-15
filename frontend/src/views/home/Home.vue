<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BIcon from '@/components/base/BIcon.vue'
import StatusTag from '@/components/data/StatusTag.vue'
import ProgressSteps from '@/components/data/ProgressSteps.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { homeApi } from '@/api/home'
import { useAsyncData } from '@/composables/useAsyncData'
import { useBadgeStore } from '@/stores/badge'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { fmtMoney } from '@/utils/format'

const router = useRouter()
const badge = useBadgeStore()
const auth = useAuthStore()
const ui = useUiStore()

const { data, loading, error, refresh } = useAsyncData('home:summary', homeApi.summary, { cacheMs: 60_000 })

onMounted(async () => {
  await refresh()
  if (data.value) badge.fromSummary(data.value)
})

/** 「412 室，上午好」→ 两行排版 */
const greet = computed(() => {
  const text = data.value?.greeting || '上午好'
  const [room, hello] = text.split('，')
  return hello ? { room, hello } : { room: '', hello: text }
})

const subtitle = computed(() => {
  const s = data.value?.subtitle || ''
  return s.replace(/\s*\/\s*/g, ' / ')
})

const activeOrder = computed(() => data.value?.latest_order ?? null)
const hasUnread = computed(() => (data.value?.unread?.total ?? 0) > 0)

function go(to: string) {
  router.push(to)
}

function openPay() {
  if (!data.value?.due?.count) {
    ui.toast('暂无待缴账单')
    return
  }
  router.push('/payment')
}

function serviceToast(en: string) {
  if (en === 'ALL') router.push('/help')
}
</script>

<template>
  <AppShell tab="home">
    <div class="page">
      <header class="top">
        <div>
          <div class="k-brand">DORM SERVICE</div>
          <h1 class="big hello">
            <template v-if="greet.room">{{ greet.room }}，<br />{{ greet.hello }}</template>
            <template v-else>{{ greet.hello }}</template>
          </h1>
          <p class="mini who">{{ auth.displayName }} / {{ subtitle }}</p>
        </div>
        <button type="button" class="bell" aria-label="消息中心" @click="go('/messages')">
          <BIcon name="bell" :size="18" />
          <span v-if="badge.unreadTotal > 0" class="dot" />
        </button>
      </header>

      <SkeletonList v-if="loading && !data" :rows="3" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <div class="duo">
          <button type="button" class="cell" @click="go('/payment')">
            <span class="mini">DUE 待缴</span>
            <span class="num-lg val">{{ fmtMoney(data.due.amount) }}</span>
          </button>
          <button type="button" class="cell" @click="go('/repair/list?status=active')">
            <span class="mini">ORDER 工单</span>
            <span class="num-lg val"><em class="red">{{ data.orders.active_count }}</em> 单</span>
          </button>
        </div>

        <div class="sec">
          <span class="l"><span class="h-cn">服务</span><span class="h-en">SERVICE</span></span>
          <span class="all">ALL 06</span>
        </div>
        <div class="svcgrid">
          <button
            v-for="s in data.services"
            :key="s.key"
            type="button"
            class="svc"
            :class="{ hot: s.hot }"
            @click="s.key === 'payment' ? openPay() : s.key === 'all' ? serviceToast(s.en) : go(s.to)"
          >
            <BIcon :name="s.icon" :size="20" />
            {{ s.label }}
            <span class="en">{{ s.en }}</span>
          </button>
        </div>

        <div class="lower">
          <div class="col-main">
            <template v-if="activeOrder">
              <div class="sec" :style="{ marginBottom: '8px' }">
                <span class="l"><span class="h-cn">工单</span><span class="h-en">ORDER</span></span>
                <span class="all">NO.{{ activeOrder.short_no }}</span>
              </div>
              <button type="button" class="orderblock" @click="go(`/repair/${activeOrder.id}`)">
                <span class="mini no">{{ activeOrder.order_no }}</span>
                <span class="row">
                  <b class="otitle">{{ activeOrder.title }}</b>
                  <StatusTag :status="activeOrder.status" size="sm" />
                </span>
                <span class="mini meta">{{ activeOrder.expect_text || (activeOrder.worker_name ? `${activeOrder.worker_name}师傅上门中` : '等待宿管受理') }}</span>
                <ProgressSteps :status="activeOrder.status" :percent="activeOrder.percent" />
              </button>
            </template>

            <button v-if="data.bill_cta" type="button" class="cta" @click="go(`/payment/bill/${data.bill_cta.id}`)">
              <span class="cta-l">
                <span class="cta-name">{{ data.bill_cta.title }}</span>
                <span class="cta-amt num-lg">{{ fmtMoney(data.bill_cta.amount) }}</span>
              </span>
              <span class="cta-r">立即缴纳 <BIcon name="chev" :size="13" /></span>
            </button>
          </div>

          <div class="col-side">
            <div class="sec">
              <span class="l"><span class="h-cn">公告</span><span class="h-en">NOTICE</span></span>
              <button type="button" class="all" @click="go('/dorm/notice')">全部</button>
            </div>
            <button v-for="n in data.notices" :key="n.id" type="button" class="notice-row" @click="go('/dorm/notice')">
              <span class="sq" />
              <span class="ntitle">{{ n.title }}</span>
              <span class="mini date">{{ n.date }}</span>
            </button>
          </div>
        </div>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-top: 6px;
}
.hello {
  font-size: clamp(32px, 2.2vw + 16px, 48px);
  line-height: 1.1;
}
.who {
  margin-top: 8px;
  text-transform: none;
  letter-spacing: 0.04em;
}
.bell {
  position: relative;
  padding: 8px;
  border: var(--line) solid var(--ink);
  border-radius: 50%;
  margin-top: 6px;
}
.bell:active {
  opacity: 0.6;
}
.dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 7px;
  height: 7px;
  background: var(--red);
  border-radius: 50%;
}
.duo {
  display: flex;
  border: var(--line) solid var(--ink);
  background: var(--panel);
  margin-top: 16px;
}
.cell {
  flex: 1;
  padding: 12px 14px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cell:first-child {
  border-right: 1px solid #d5d5d3;
}
.cell:active {
  opacity: 0.6;
}
.val {
  font-size: 24px;
}
.val em {
  font-style: normal;
}
.svc {
  color: var(--ink);
}
.orderblock {
  display: flex;
  flex-direction: column;
  width: 100%;
  text-align: left;
  padding: 2px 0 4px;
}
.orderblock:active {
  opacity: 0.7;
}
.no {
  color: #b9b9b7;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-top: 4px;
}
.otitle {
  font-size: 14px;
  font-weight: 800;
  line-height: 1.35;
}
.meta {
  margin-top: 4px;
  text-transform: none;
  letter-spacing: 0.03em;
  display: block;
}
.cta {
  margin-top: 16px;
  background: var(--ink);
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  width: 100%;
  text-align: left;
}
.cta:active {
  opacity: 0.6;
}
.cta-l {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.cta-name {
  font-size: 11px;
  color: #c9c9c7;
  letter-spacing: 0.02em;
}
.cta-amt {
  font-size: 19px;
}
.cta-r {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  flex: none;
}
.notice-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 0;
  width: 100%;
  text-align: left;
  border-bottom: 1px solid var(--hair);
}
.notice-row:last-child {
  border-bottom: none;
}
.sq {
  width: 5px;
  height: 5px;
  background: var(--red);
  flex: none;
}
.ntitle {
  font-size: 12px;
  font-weight: 700;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.date {
  flex: none;
}

/* ---------- 桌面：主栏 + 侧栏两栏 ---------- */
@media (min-width: 1024px) {
  .top {
    margin-top: 0;
    align-items: center;
  }

  .duo {
    margin-top: 24px;
  }

  .cell {
    padding: 18px 22px;
    gap: 8px;
  }

  .svcgrid {
    margin-top: 0;
  }

  .lower {
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr);
    gap: 40px;
    align-items: start;
  }

  .col-side {
    border-left: 1px solid var(--hair);
    padding-left: 32px;
    min-width: 0;
  }

  .col-main {
    min-width: 0;
  }

  /* 侧栏第一块标题与主栏工单标题对齐 */
  .col-side .sec:first-child {
    margin-top: 26px;
  }

  .orderblock {
    padding: 20px 22px;
  }

  .otitle {
    font-size: 16px;
  }

  .cta {
    margin-top: 20px;
    padding: 20px 24px;
  }

  .cta-amt {
    font-size: 26px;
  }

  .cta-name,
  .cta-r {
    font-size: 12px;
  }

  .notice-row {
    padding: 13px 0;
  }

  .ntitle {
    font-size: 14px;
  }
}
</style>
