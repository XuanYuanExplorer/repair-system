<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import BSwitch from '@/components/base/BSwitch.vue'
import BTag from '@/components/base/BTag.vue'
import StarRating from '@/components/data/StarRating.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { repairApi } from '@/api/repair'
import { errText, isBizError } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import { repairDirty } from '@/utils/dirty'
import { charLen } from '@/utils/validate'
import { fmtMoney } from '@/utils/format'

const props = defineProps<{ id: string }>()
const router = useRouter()
const ui = useUiStore()
const orderId = computed(() => Number(props.id))

const { data, loading, error, refresh } = useAsyncData(`repair-rate:${props.id}`, () => repairApi.detail(orderId.value))

const score = reactive({ speed: 5, attitude: 5, quality: 5 })
const content = ref('')
const anonymous = ref(false)
const repairing = ref(false)
const reworkOpen = ref(false)
const reworkReason = ref('')
const submitting = ref(false)

const canVerify = computed(() => data.value?.status === 'verify')
const done = computed(() => data.value?.status === 'done')
const rated = computed(() => !!data.value?.rating)
const rateOpen = computed(() => done.value && !rated.value && !!data.value?.can_rate)
const rateClosed = computed(() => done.value && !rated.value && !data.value?.can_rate)

/** 完工说明要点：优先后端 fix_note，逐句拆分；附材料费提示 */
const resultLines = computed(() => {
  const note = data.value?.fix_note || '师傅已完成维修并测试通过。'
  return note
    .split(/[；;\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 4)
})

onMounted(refresh)

function syncDirty() {
  repairDirty.value = true
}

async function verifyResolved() {
  submitting.value = true
  try {
    await repairApi.verify(orderId.value, true)
    syncDirty()
    ui.toast('已确认完工，请为本次服务评分')
    await refresh(true)
  } catch (e) {
    if (isBizError(e) && e.code === 3001) await refresh(true)
    ui.toast(errText(e, '确认失败'), 'red')
  } finally {
    submitting.value = false
  }
}

async function submitRework() {
  if (charLen(reworkReason.value.trim()) < 4) {
    ui.toast('请填写返修原因（至少 4 个字）', 'red')
    return
  }
  repairing.value = true
  try {
    await repairApi.verify(orderId.value, false, reworkReason.value.trim())
    reworkOpen.value = false
    syncDirty()
    ui.toast('已申请返修，宿管将重新派单')
    await router.replace(`/repair/${orderId.value}`)
  } catch (e) {
    if (isBizError(e) && e.code === 3001) await refresh(true)
    ui.toast(errText(e, '提交失败'), 'red')
  } finally {
    repairing.value = false
  }
}

async function submitRate() {
  submitting.value = true
  try {
    await repairApi.rate(orderId.value, { ...score, content: content.value.trim() || undefined, is_anonymous: anonymous.value })
    syncDirty()
    ui.toast('评价已提交，感谢反馈')
    await router.replace('/repair/list')
  } catch (e) {
    if (isBizError(e) && e.code === 3007) {
      ui.toast('该工单已评价', 'red')
      await refresh(true)
    } else if (isBizError(e) && e.code === 3006) {
      ui.toast('评价已关闭（超过 7 天）', 'red')
    } else {
      ui.toast(errText(e, '提交失败'), 'red')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <SkeletonList v-if="loading && !data" :rows="4" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <PageHeader kicker="VERIFY / 完工确认" title="确认与评价" :subtitle="`${data.order_no} · ${data.category_label} · ${data.location_desc}`" back @back="router.back()" />

        <div class="sec">
          <span class="l"><span class="h-cn">维修结果核对</span><span class="h-en">RESULT</span></span>
          <BTag v-if="canVerify" tone="red" text="待确认" />
          <BTag v-else-if="done" tone="gray" text="已确认" />
        </div>
        <div class="panel result">
          <p v-for="(line, i) in resultLines" :key="i">· {{ line }}</p>
          <button
            v-if="Number(data.material_fee) > 0"
            type="button"
            class="fee"
            @click="router.push('/payment')"
          >
            材料费 {{ fmtMoney(data.material_fee) }} 已另立账单 <span>查看 →</span>
          </button>
        </div>

        <div v-if="canVerify" class="btn-row">
          <BButton :loading="submitting" @click="verifyResolved">已修好，确认完工</BButton>
          <BButton variant="ghost-red" @click="reworkOpen = true">未解决 · 申请返修</BButton>
        </div>

        <template v-if="rateOpen">
          <div class="sec"><span class="l"><span class="h-cn">服务评价</span><span class="h-en">RATE</span></span></div>
          <div class="rowline"><span class="rlabel">维修速度</span><StarRating v-model="score.speed" label="维修速度" /></div>
          <div class="rowline"><span class="rlabel">服务态度</span><StarRating v-model="score.attitude" label="服务态度" /></div>
          <div class="rowline"><span class="rlabel">维修质量</span><StarRating v-model="score.quality" label="维修质量" /></div>

          <div class="sec" :style="{ marginBottom: '6px' }">
            <span class="l"><span class="h-cn">文字评价</span><span class="h-en">COMMENT</span></span>
            <span class="all">{{ charLen(content) }}/40</span>
          </div>
          <textarea v-model="content" class="desc" maxlength="40" placeholder="填写文字评价（选填，40 字以内）" />

          <div class="rowline anon">
            <span class="rlabel">匿名提交评价</span>
            <BSwitch v-model="anonymous" label="匿名提交评价" />
          </div>

          <div class="spacer" />
          <BButton :loading="submitting" @click="submitRate">提交评价并归档</BButton>
          <p class="hint">评价将计入维修人员绩效，提交后工单关闭</p>
        </template>

        <div v-else-if="rated" class="panel rated">
          <p class="mini">已评价</p>
          <div class="rated-row">
            <span class="num-lg big-score">{{ Number((data.rating?.speed! + data.rating?.attitude! + data.rating?.quality!) / 3).toFixed(1) }}</span>
            <StarRating :model-value="5" readonly :size="14" />
          </div>
          <p v-if="data.rating?.content" class="rated-txt">“{{ data.rating.content }}”</p>
          <BButton variant="ghost" size="sm" class="backbtn" @click="router.replace('/repair/list')">返回我的报修</BButton>
        </div>

        <p v-else-if="rateClosed" class="hint closed">评价已关闭（完工超过 7 天）</p>

        <BSheet v-model="reworkOpen" title="申请返修">
          <p class="sheetdesc">请说明仍未解决的问题，宿管中心将重新派单。</p>
          <textarea v-model="reworkReason" class="desc" maxlength="100" placeholder="例如：出风口仍不制冷，温度 28℃" />
          <template #footer>
            <BButton variant="ghost-red" :loading="repairing" @click="submitRework">提交返修申请</BButton>
          </template>
        </BSheet>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.result {
  padding: 12px 14px;
  font-size: 11.5px;
  line-height: 1.9;
  border: 1px solid var(--hair);
}
.fee {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--hair);
  font-size: 11px;
  font-weight: 700;
  color: var(--red);
}
.rlabel {
  font-size: 12px;
  font-weight: 700;
}
.anon {
  margin-top: 8px;
}
.hint {
  font-size: 9px;
  color: var(--mute);
  text-align: center;
  margin-top: 10px;
  line-height: 1.7;
}
.hint.closed {
  margin-top: 20px;
}
.rated {
  padding: 14px;
  border: 1px solid var(--hair);
  margin-top: 16px;
}
.rated-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}
.big-score {
  font-size: 26px;
}
.rated-txt {
  font-size: 11.5px;
  color: #2a2a2a;
  margin-top: 8px;
  line-height: 1.7;
}
.backbtn {
  margin-top: 12px;
}
.sheetdesc {
  font-size: 11px;
  color: var(--mute);
  line-height: 1.7;
  margin: 6px 0 10px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}
</style>
