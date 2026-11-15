<script setup lang="ts">
import { computed } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import StarRating from '@/components/data/StarRating.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { repairApi } from '@/api/repair'
import { useAsyncData } from '@/composables/useAsyncData'
import { fmtDay } from '@/utils/format'

const { data, loading, error, refresh } = useAsyncData('repair:archive', repairApi.archive)

const maxCount = computed(() => Math.max(...(data.value?.distribution || []).map((d) => d.count), 1))
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="ARCHIVE" title="我的维修档案" :subtitle="data?.since ? `${data.since} · 数据每周更新` : '入住至今 · 数据每周更新'" back @back="$router.back()" />

      <SkeletonList v-if="loading && !data" :rows="3" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <div class="statgrid stats">
          <div>
            <span class="mini">报修次数</span>
            <span class="num-lg v">{{ data.total_count }}</span>
          </div>
          <div>
            <span class="mini">平均时长</span>
            <span class="num-lg v">{{ data.avg_duration_days }}<em> 天</em></span>
          </div>
          <div>
            <span class="mini">好评率</span>
            <span class="num-lg v"><em class="red">{{ data.good_rate }}</em><em>%</em></span>
          </div>
        </div>

        <div class="sec"><span class="l"><span class="h-cn">类别分布</span><span class="h-en">BY TYPE</span></span></div>
        <div class="bars">
          <div v-for="d in data.distribution" :key="d.category" class="barrow">
            <span class="label">{{ d.label }}</span>
            <span class="bar"><i :style="{ width: `${Math.round((d.count / maxCount) * 100)}%`, background: d.alert ? 'var(--red)' : 'var(--ink)' }" /></span>
            <span class="num-lg cnt">{{ d.count }}</span>
          </div>
        </div>

        <div v-if="data.repeat_alert" class="notice alert">
          {{ data.repeat_alert.text }}
        </div>

        <template v-if="data.recent_ratings.length">
          <div class="sec"><span class="l"><span class="h-cn">最近评价</span><span class="h-en">RATINGS</span></span></div>
          <div v-for="(r, i) in data.recent_ratings" :key="i" class="rateline">
            <div class="rtop">
              <span class="num-lg score">{{ Number(r.score).toFixed(1) }}</span>
              <StarRating :model-value="Math.round(r.score)" readonly :size="13" />
              <span class="mini date">{{ fmtDay(r.created_at) }}</span>
            </div>
            <p v-if="r.content" class="rtext">{{ r.content }}</p>
            <p v-else class="rtext mute">未填写文字评价</p>
          </div>
        </template>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.stats {
  margin-top: 18px;
}
.stats > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 13px 14px;
}
.v {
  font-size: 26px;
  display: flex;
  align-items: baseline;
  gap: 1px;
}
.v em {
  font-style: normal;
  font-size: 12px;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.barrow {
  display: flex;
  align-items: center;
  gap: 10px;
}
.label {
  width: 52px;
  flex: none;
  font-size: 10px;
  color: var(--ink);
  font-weight: 600;
}
.cnt {
  font-size: 13px;
  width: 22px;
  text-align: right;
  flex: none;
}
.alert {
  margin-top: 18px;
  line-height: 1.7;
}
.rateline {
  padding: 11px 0;
  border-bottom: 1px solid var(--hair);
}
.rateline:last-child {
  border-bottom: none;
}
.rtop {
  display: flex;
  align-items: center;
  gap: 8px;
}
.score {
  font-size: 16px;
}
.date {
  margin-left: auto;
}
.rtext {
  font-size: 11px;
  color: #3a3a3a;
  margin-top: 5px;
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
