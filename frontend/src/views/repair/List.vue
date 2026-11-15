<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import SearchInput from '@/components/form/SearchInput.vue'
import OrderCard from '@/components/data/OrderCard.vue'
import EmptyState from '@/components/feedback/EmptyState.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { repairApi } from '@/api/repair'
import { errText } from '@/api/client'
import { ORDER_STATUS_TABS, CATEGORY_LIST } from '@/utils/dict'
import { repairDirty } from '@/utils/dirty'
import { useDebouncedRef } from '@/composables/useDebounce'
import type { OrderBrief } from '@/api/types'

defineOptions({ name: 'RepairList' })

const route = useRoute()
const router = useRouter()

const status = ref(typeof route.query.status === 'string' ? route.query.status : 'all')
const keyword = ref('')
const debouncedKeyword = useDebouncedRef(keyword, 300)
const category = ref('all')

const list = ref<OrderBrief[]>([])
const counts = ref<Record<string, number>>({})
const total = ref(0)
const page = ref(1)
const hasMore = ref(false)
const loading = ref(true)
const loadingMore = ref(false)
const error = ref('')
const sentinel = ref<HTMLElement | null>(null)

const currentTabLabel = computed(() => ORDER_STATUS_TABS.find((t) => t.value === status.value)?.label || '全部')

function tabCount(value: string): number {
  if (value === 'all') return Object.values(counts.value).reduce((a, b) => a + b, 0)
  if (value === 'active') return (counts.value.pending || 0) + (counts.value.assigned || 0) + (counts.value.fixing || 0) + (counts.value.verify || 0)
  return counts.value[value] || 0
}

async function fetchPage(reset = false) {
  if (reset) {
    page.value = 1
    loading.value = true
    error.value = ''
  } else {
    loadingMore.value = true
  }
  try {
    const res = await repairApi.list({
      status: status.value,
      category: category.value === 'all' ? undefined : category.value,
      keyword: debouncedKeyword.value || undefined,
      page: page.value,
      page_size: 12,
    })
    list.value = reset ? res.items : [...list.value, ...res.items]
    counts.value = res.counts || {}
    total.value = res.total
    hasMore.value = res.has_more
    page.value += 1
  } catch (e) {
    error.value = errText(e, '加载失败，请稍后重试')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  if (!hasMore.value || loading.value || loadingMore.value) return
  await fetchPage(false)
}

watch([status, debouncedKeyword, category], () => {
  router.replace({ query: status.value === 'all' ? {} : { status: status.value } })
  void fetchPage(true)
})

onMounted(() => {
  void fetchPage(true)
  const io = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) void loadMore()
    },
    { rootMargin: '120px' },
  )
  watch(
    sentinel,
    (el) => {
      if (el) io.observe(el)
    },
    { immediate: true },
  )
})

onActivated(() => {
  if (repairDirty.value) {
    repairDirty.value = false
    void fetchPage(true)
  }
})

function open(id: number) {
  router.push(`/repair/${id}`)
}
</script>

<template>
  <AppShell tab="repair">
    <div class="page">
      <div class="k-brand">MY ORDERS</div>
      <h1 class="big title">我的报修</h1>

      <SearchInput v-model="keyword" placeholder="搜索工单号 / 故障关键词" />

      <div class="tabs" role="tablist">
        <button
          v-for="t in ORDER_STATUS_TABS"
          :key="t.value"
          type="button"
          class="tab"
          :class="{ on: status === t.value }"
          role="tab"
          :aria-selected="status === t.value"
          @click="status = t.value"
        >
          {{ t.label }}<em v-if="tabCount(t.value)">{{ tabCount(t.value) }}</em>
        </button>
      </div>

      <div class="filters">
        <select v-model="category" class="mini-select" aria-label="按类别筛选">
          <option value="all">全部类别</option>
          <option v-for="c in CATEGORY_LIST" :key="c.value" :value="c.value">{{ c.label }}</option>
        </select>
        <span class="mini count">共 {{ total }} 条</span>
      </div>

      <SkeletonList v-if="loading" :rows="3" />
      <ErrorRetry v-else-if="error" :message="error" @retry="fetchPage(true)" />
      <template v-else>
        <div v-if="list.length" class="cards">
          <OrderCard v-for="o in list" :key="o.id" :order="o" @open="open(o.id)" />
        </div>
        <EmptyState
          v-else
          :title="`暂无${currentTabLabel}的工单`"
          desc="提交报修后，宿管中心会在 24 小时内响应"
          action-text="去报修"
          icon="tool"
          @action="router.push('/repair/submit')"
        />

        <div ref="sentinel" class="sentinel">
          <span v-if="loadingMore" class="mini">加载中…</span>
          <span v-else-if="!hasMore && list.length" class="mini">— 已显示全部 {{ total }} 条 —</span>
        </div>
      </template>

      <button type="button" class="fab" aria-label="新建报修" @click="router.push('/repair/submit')">＋</button>
    </div>
  </AppShell>
</template>

<style scoped>
.title {
  font-size: 28px;
  margin-top: 2px;
}
.tabs {
  display: flex;
  gap: 14px;
  margin-top: 14px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  overflow-x: auto;
  white-space: nowrap;
  padding-bottom: 6px;
  scrollbar-width: none;
}
.tabs::-webkit-scrollbar {
  display: none;
}
.tab {
  color: var(--mute);
  flex: none;
  padding-bottom: 4px;
  border-bottom: 2.5px solid transparent;
}
.tab em {
  font-style: normal;
  margin-left: 3px;
  font-size: 9px;
}
.tab.on {
  color: var(--red);
  border-bottom-color: var(--red);
}
.filters {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  margin-bottom: 12px;
}
.mini-select {
  width: auto;
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--mute);
  font-weight: 700;
  text-transform: uppercase;
  flex: none;
}
.count {
  margin-left: auto;
}
.sentinel {
  text-align: center;
  padding: 14px 0 4px;
  min-height: 30px;
}
.fab {
  position: fixed;
  right: max(22px, calc(50vw - var(--page-max) / 2 + 22px));
  bottom: calc(var(--tabbar-h) + 30px + env(safe-area-inset-bottom));
  width: 46px;
  height: 46px;
  background: var(--ink);
  color: #fff;
  font-size: 22px;
  font-weight: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.fab:active {
  opacity: 0.6;
}

/* ---------- 桌面：两列卡片 ---------- */
@media (min-width: 1024px) {
  .cards {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    align-items: start;
  }

  .cards :deep(.card) {
    border: var(--line) solid var(--ink);
    padding: 18px 20px;
  }

  .cards :deep(.card.muted) {
    border-color: var(--hair);
  }

  .filters {
    margin-top: 4px;
  }

  .mini-select {
    font-size: 13px;
    padding: 8px 10px;
  }
}
</style>
