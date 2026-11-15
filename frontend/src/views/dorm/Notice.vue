<script setup lang="ts">
import { computed, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BTag from '@/components/base/BTag.vue'
import BButton from '@/components/base/BButton.vue'
import BIcon from '@/components/base/BIcon.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { noticeApi } from '@/api/notice'
import { dormApi } from '@/api/dorm'
import { errText } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import { useBadgeStore } from '@/stores/badge'
import type { Notice } from '@/api/types'

const ui = useUiStore()
const badge = useBadgeStore()
const list = useAsyncData('notices', () => noticeApi.list({ page_size: 30 }))
const rules = useAsyncData('dorm:rules', dormApi.rules)

const expanded = ref<number | null>(null)
const receipts = ref<Record<number, boolean>>({})

const notices = computed(() => list.data.value?.items || [])
const pinned = computed(() => notices.value.find((n) => n.is_pinned) || null)
const rest = computed(() => notices.value.filter((n) => n.id !== pinned.value?.id))
const unread = computed(() => list.data.value?.unread ?? 0)
const progress = computed(() => list.data.value?.receipt_progress)

async function toggle(n: Notice) {
  if (expanded.value === n.id) {
    expanded.value = null
    return
  }
  expanded.value = n.id
  if (!n.is_read) {
    try {
      await noticeApi.read(n.id)
      n.is_read = true
      badge.decUnread()
      await list.refresh(true)
    } catch {
      // 已读标记失败不打断阅读
    }
  }
}

async function receipt(n: Notice) {
  try {
    await noticeApi.receipt(n.id)
    receipts.value = { ...receipts.value, [n.id]: true }
    ui.toast('已回执，宿管中心将同步统计')
    await list.refresh(true)
  } catch (e) {
    ui.toast(errText(e, '回执失败'), 'red')
  }
}

function hasReceipt(n: Notice): boolean {
  return !!n.receipt_at || !!receipts.value[n.id]
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="NOTICE / RULES" title="公告与公约" back @back="$router.back()" />

      <div class="sec">
        <span class="l"><span class="h-cn">宿管中心通知</span><span class="h-en">NOTICE</span></span>
        <span class="all" :class="{ red: unread > 0 }">未读 {{ unread }}</span>
      </div>

      <SkeletonList v-if="list.loading.value && !notices.length" :rows="3" variant="card" />
      <ErrorRetry v-else-if="list.error.value" :message="list.error.value" @retry="list.refresh()" />

      <template v-else>
        <article v-if="pinned" class="pinned">
          <div class="ptop">
            <BTag tone="red" text="置顶" />
            <span class="mini">{{ pinned.date_text }} · {{ pinned.publisher }}</span>
          </div>
          <b class="ptitle">{{ pinned.title }}</b>
          <p class="psum" :class="{ open: expanded === pinned.id }">{{ expanded === pinned.id ? pinned.content : pinned.summary }}</p>
          <div class="pfoot">
            <span class="mini unread" :class="{ red: !pinned.is_read }">
              ● {{ !pinned.is_read ? '未读' : '已读' }}<template v-if="progress"> {{ progress.read }}/{{ progress.total }}</template>
              <template v-if="pinned.require_receipt"> · {{ hasReceipt(pinned) ? '已回执' : '待回执' }}</template>
            </span>
            <div class="pfright">
              <button type="button" class="btn-text ink" @click="toggle(pinned)">{{ expanded === pinned.id ? '收起' : '展开' }}</button>
              <BButton v-if="pinned.require_receipt && !hasReceipt(pinned)" size="sm" class="receiptbtn" @click="receipt(pinned)">回执确认</BButton>
              <span v-else-if="pinned.require_receipt" class="tag gray sm">已回执</span>
            </div>
          </div>
        </article>

        <div v-for="n in rest" :key="n.id" class="item">
          <button type="button" class="ihead" @click="toggle(n)">
            <span class="dot" :class="{ on: !n.is_read }" />
            <span class="ititle">{{ n.title }}</span>
            <span class="mini idate">{{ n.date_text.slice(0, 5) }}</span>
            <BIcon :name="expanded === n.id ? 'minus' : 'chev'" :size="12" class="ichev" />
          </button>
          <div v-if="expanded === n.id" class="ibody">
            <p class="icontent">{{ n.content }}</p>
            <div class="ifoot">
              <span class="mini">{{ n.publisher }} · {{ n.type_label }}</span>
              <BButton v-if="n.require_receipt && !hasReceipt(n)" size="sm" variant="ghost" class="receiptbtn" @click="receipt(n)">回执确认</BButton>
              <span v-else-if="n.require_receipt" class="tag gray sm">已回执</span>
            </div>
          </div>
        </div>

        <div class="sec">
          <span class="l"><span class="h-cn">本寝公约</span><span class="h-en">RULES</span></span>
          <span class="all">寝室长维护</span>
        </div>
        <ol class="rules">
          <li v-for="(r, i) in rules.data.value?.items || []" :key="i">
            <span class="idx num-lg">{{ String(i + 1).padStart(2, '0') }}</span>
            <span>{{ r.content }}</span>
          </li>
          <li v-if="!rules.data.value?.items?.length" class="mute empty">寝室长尚未维护公约</li>
        </ol>

        <p class="hint">● 已读标记用于回执统计 · 宿管可查看未读人员名单</p>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.pinned {
  border: var(--line) solid var(--ink);
  padding: 13px 14px;
  background: var(--panel);
}
.ptop {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ptitle {
  font-size: 13.5px;
  display: block;
  margin-top: 8px;
}
.psum {
  font-size: 11px;
  color: #5a5a58;
  margin-top: 5px;
  line-height: 1.7;
  white-space: pre-line;
}
.psum.open {
  color: #2a2a2a;
}
.pfoot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.pfright {
  display: flex;
  align-items: center;
  gap: 8px;
}
.unread {
  text-transform: none;
  letter-spacing: 0.02em;
}
.receiptbtn {
  width: auto;
  margin-top: 0;
  padding: 7px 14px;
  font-size: 10px;
  letter-spacing: 0.08em;
  min-height: 30px;
}
.item {
  border-bottom: 1px solid var(--hair);
}
.ihead {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 0;
  text-align: left;
}
.dot {
  width: 6px;
  height: 6px;
  background: #d5d5d3;
  border-radius: 50%;
  flex: none;
}
.dot.on {
  background: var(--red);
}
.ititle {
  font-size: 12.5px;
  font-weight: 700;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.idate {
  flex: none;
}
.ichev {
  color: var(--ghost);
  flex: none;
}
.ibody {
  padding: 0 0 12px 14px;
}
.icontent {
  font-size: 11px;
  line-height: 1.8;
  color: #3a3a3a;
  white-space: pre-line;
}
.ifoot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  gap: 8px;
}
.rules {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 4px 0;
}
.rules li {
  display: flex;
  gap: 10px;
  font-size: 11px;
  line-height: 1.7;
}
.idx {
  font-size: 10px;
  color: var(--mute);
  flex: none;
  padding-top: 1px;
}
.empty {
  font-size: 11px;
}
.hint {
  font-size: 9px;
  color: var(--mute);
  margin-top: 16px;
  line-height: 1.7;
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
