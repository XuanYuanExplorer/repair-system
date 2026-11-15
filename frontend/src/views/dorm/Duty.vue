<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import BIcon from '@/components/base/BIcon.vue'
import BTag from '@/components/base/BTag.vue'
import PhotoUploader from '@/components/form/PhotoUploader.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { dutyApi } from '@/api/duty'
import { errText } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import { HYGIENE_LEVEL, statusOf } from '@/utils/dict'
import { fmtDate } from '@/utils/format'
import type { HygieneCheck } from '@/api/types'

const ui = useUiStore()
const weekStart = ref<string>('')
const schedule = useAsyncData('duty:schedule', () => dutyApi.schedule(weekStart.value || undefined))
const checks = useAsyncData('hygiene:checks', () => dutyApi.checks({ page_size: 12 }))

const generating = ref(false)
const rectifyOpen = ref(false)
const rectifyTarget = ref<HygieneCheck | null>(null)
const rectifyMedia = ref<string[]>([])
const submitting = ref(false)

const items = computed(() => schedule.data.value?.items || [])
const today = computed(() => schedule.data.value?.today || null)
const areas = computed(() => schedule.data.value?.areas || [])
const canEdit = computed(() => !!schedule.data.value?.can_edit)
const average = computed(() => checks.data.value?.average ?? 0)

function shiftWeek(delta: number) {
  const base = schedule.data.value?.week_start || fmtDate(new Date())
  const d = new Date(`${base}T00:00:00`)
  d.setDate(d.getDate() + delta * 7)
  weekStart.value = fmtDate(d)
}

function backThisWeek() {
  weekStart.value = ''
  void schedule.refresh()
}

watch(weekStart, () => schedule.refresh())

onMounted(async () => {
  await schedule.refresh()
})

async function generate() {
  generating.value = true
  try {
    await dutyApi.generate(schedule.data.value?.week_start)
    ui.toast('本周排班已生成')
    await schedule.refresh(true)
  } catch (e) {
    ui.toast(errText(e, '生成失败'), 'red')
  } finally {
    generating.value = false
  }
}

function openRectify(c: HygieneCheck) {
  rectifyTarget.value = c
  rectifyMedia.value = []
  rectifyOpen.value = true
}

async function submitRectify() {
  if (!rectifyTarget.value) return
  if (!rectifyMedia.value.length) {
    ui.toast('请至少上传 1 张整改照片', 'red')
    return
  }
  submitting.value = true
  try {
    await dutyApi.rectify(rectifyTarget.value.id, rectifyMedia.value)
    rectifyOpen.value = false
    ui.toast('整改照片已提交')
    await checks.refresh(true)
  } catch (e) {
    ui.toast(errText(e, '提交失败'), 'red')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader
        kicker="DUTY / HYGIENE"
        title="值日与卫生检查"
        :subtitle="schedule.data.value ? `第 ${schedule.data.value.week_no} 周 · 每日轮换` : undefined"
        back
        @back="$router.back()"
      />

      <div class="sec">
        <span class="l"><span class="h-cn">本周值日表</span><span class="h-en">W{{ String(schedule.data.value?.week_no ?? '').padStart(2, '0') }}</span></span>
        <span class="weeknav">
          <button type="button" aria-label="上一周" @click="shiftWeek(-1)"><BIcon name="chev" :size="12" class="left" /></button>
          <button type="button" class="thisweek" @click="backThisWeek">本周</button>
          <button type="button" aria-label="下一周" @click="shiftWeek(1)"><BIcon name="chev" :size="12" /></button>
        </span>
      </div>

      <SkeletonList v-if="schedule.loading.value && !schedule.data.value" :rows="2" variant="detail" />
      <ErrorRetry v-else-if="schedule.error.value && !schedule.data.value" :message="schedule.error.value" @retry="schedule.refresh()" />

      <template v-else-if="schedule.data.value">
        <div v-if="schedule.data.value.is_empty" class="dash emptyweek">
          <BIcon name="cal" :size="20" />
          <span class="mini">本周尚未排班</span>
        </div>
        <template v-else>
          <div class="week">
            <div v-for="d in items" :key="d.id" class="day" :class="{ today: d.is_today }">
              <span class="wd">{{ d.weekday_cn }}{{ d.is_today ? '·今' : '' }}</span>
              <span class="who">{{ d.short_name || '—' }}</span>
            </div>
          </div>
          <div class="arealine">
            <span class="mini">区域</span>
            <span class="areatext">{{ areas.join(' / ') }}</span>
          </div>
          <div v-if="today" class="todayline">
            <span>今日值日 · <b>{{ today.user_name }}</b></span>
            <span class="mini" :class="{ red: !today.reminded }">{{ today.reminded ? '已推送提醒' : '待推送提醒' }}</span>
          </div>
        </template>

        <div class="sec">
          <span class="l"><span class="h-cn">卫生检查记录</span><span class="h-en">CHECK</span></span>
          <span class="all">学期均分 {{ average }}</span>
        </div>

        <SkeletonList v-if="checks.loading.value && !checks.data.value" :rows="3" variant="row" />
        <div v-for="c in checks.data.value?.items || []" :key="c.id" class="check">
          <div class="chead">
            <span class="cdate">{{ c.date_text }} · 第 {{ c.week_no }} 周</span>
            <span class="cscore">
              <span class="num-lg">{{ c.score }}</span>
              <BTag :text="c.level_label" :tone="statusOf(HYGIENE_LEVEL, c.level).tone === 'red' ? 'red' : 'ink'" sm />
            </span>
          </div>
          <div class="cline">
            <span :class="{ red: c.deductions.length }">{{ c.deduction_text }}</span>
            <button v-if="c.can_rectify" type="button" class="btn-text rectifybtn" @click="openRectify(c)">
              {{ c.rectify_status === 'submitted' ? '已提交' : '整改回复 · 上传照片' }}
            </button>
          </div>
          <div v-if="c.rectify_media.length" class="thumbs">
            <img v-for="(m, i) in c.rectify_media" :key="i" :src="m" alt="整改照片" loading="lazy" />
          </div>
        </div>

        <div v-if="canEdit" class="spacer" />
        <BButton v-if="canEdit" variant="ghost" :loading="generating" @click="generate">生成本周排班 · 按轮换规则滚动</BButton>
      </template>

      <BSheet v-model="rectifyOpen" title="整改回复">
        <p class="sheetdesc">{{ rectifyTarget?.requirement || '请上传整改后的现场照片（1–4 张）' }}</p>
        <PhotoUploader v-model="rectifyMedia" :max="4" biz-type="hygiene" />
        <template #footer>
          <BButton :loading="submitting" @click="submitRectify">提交整改</BButton>
        </template>
      </BSheet>
    </div>
  </AppShell>
</template>

<style scoped>
.weeknav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.weeknav button {
  border: 1px solid var(--hair);
  width: 22px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--mute);
}
.weeknav .thisweek {
  width: auto;
  padding: 0 7px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.left {
  transform: rotate(180deg);
}
.week {
  display: flex;
  border: var(--line) solid var(--ink);
}
.day {
  flex: 1;
  text-align: center;
  padding: 9px 0;
  border-right: 1px solid #d5d5d3;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.day:last-child {
  border-right: none;
}
.day.today {
  background: var(--ink);
  color: #fff;
  border-right-color: var(--ink);
}
.wd {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--mute);
  font-weight: 700;
}
.day.today .wd {
  color: #9a9a9a;
}
.who {
  font-size: 11px;
  font-weight: 700;
}
.arealine {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  align-items: baseline;
}
.areatext {
  font-size: 11px;
  font-weight: 600;
}
.todayline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 11px;
}
.emptyweek {
  height: 92px;
  gap: 6px;
}
.check {
  padding: 11px 0;
  border-bottom: 1px solid var(--hair);
}
.chead {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cdate {
  font-size: 11px;
  font-weight: 700;
}
.cscore {
  display: flex;
  align-items: center;
  gap: 6px;
}
.cscore .num-lg {
  font-size: 15px;
}
.cline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 5px;
  font-size: 10px;
  color: var(--mute);
}
.rectifybtn {
  font-size: 9px;
  flex: none;
  color: var(--red);
}
.thumbs {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.thumbs img {
  width: 46px;
  height: 46px;
  object-fit: cover;
  border: 1px solid var(--hair);
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
</style>
