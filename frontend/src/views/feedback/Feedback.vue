<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BChip from '@/components/base/BChip.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import BIcon from '@/components/base/BIcon.vue'
import BTag from '@/components/base/BTag.vue'
import StarRating from '@/components/data/StarRating.vue'
import PhotoUploader from '@/components/form/PhotoUploader.vue'
import { feedbackApi } from '@/api/feedback'
import { repairApi } from '@/api/repair'
import { errText } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import { charLen } from '@/utils/validate'
import { FEEDBACK_STATUS, FEEDBACK_TYPE, statusOf } from '@/utils/dict'
import type { Feedback, OrderBrief } from '@/api/types'

const ui = useUiStore()

const TYPES = Object.entries(FEEDBACK_TYPE).map(([value, label]) => ({ value, label }))
const form = reactive({ type: 'charge', order_id: null as number | null, content: '', media: [] as string[] })
const typeError = ref('')
const descError = ref('')
const submitting = ref(false)

const history = ref<Feedback[]>([])
const orders = ref<OrderBrief[]>([])
const orderOpen = ref(false)
const ratingOpen = ref(false)
const ratingTarget = ref<Feedback | null>(null)
const ratingScore = ref(5)

const linkedOrder = computed(() => orders.value.find((o) => o.id === form.order_id) || null)
const descLen = computed(() => charLen(form.content))
const canSubmit = computed(() => !!form.type && descLen.value >= 10 && !submitting.value)

async function loadHistory() {
  try {
    const res = await feedbackApi.list({ page_size: 20 })
    history.value = res.items
  } catch (e) {
    ui.toast(errText(e, '历史反馈加载失败'), 'red')
  }
}

async function loadOrders() {
  try {
    const res = await repairApi.list({ status: 'done', page_size: 20 })
    orders.value = res.items
  } catch {
    // 已完成工单加载失败时仍可提交不关联反馈
  }
}

onMounted(() => {
  void loadHistory()
  void loadOrders()
})

async function submit() {
  typeError.value = form.type ? '' : '请选择反馈类型'
  descError.value = descLen.value >= 10 ? '' : '请至少填写 10 个字，便于核实处理'
  if (typeError.value || descError.value) return
  submitting.value = true
  try {
    const res = await feedbackApi.create({
      type: form.type,
      order_id: form.order_id,
      content: form.content.trim(),
      media_urls: form.media,
    })
    ui.toast(`反馈已提交 ${res.fb_no}，可在下方查看进度`)
    form.content = ''
    form.media = []
    form.order_id = null
    await loadHistory()
  } catch (e) {
    ui.toast(errText(e, '提交失败，请稍后重试'), 'red')
  } finally {
    submitting.value = false
  }
}

async function rate() {
  if (!ratingTarget.value) return
  try {
    await feedbackApi.satisfaction(ratingTarget.value.id, ratingScore.value)
    ratingOpen.value = false
    ui.toast('感谢你的评价')
    await loadHistory()
  } catch (e) {
    ui.toast(errText(e, '评价失败'), 'red')
  }
}

function openRating(f: Feedback) {
  ratingTarget.value = f
  ratingScore.value = 5
  ratingOpen.value = true
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="FEEDBACK" title="意见反馈 / 投诉建议" back @back="$router.back()" />

      <div class="sec" :style="{ marginBottom: '8px' }"><span class="l"><span class="h-cn">反馈类型</span><span class="h-en">TYPE</span></span></div>
      <div class="chips">
        <BChip v-for="t in TYPES" :key="t.value" :on="form.type === t.value" @click="form.type = t.value">{{ t.label }}</BChip>
      </div>
      <p v-if="typeError" class="errtext">▲ {{ typeError }}</p>

      <div class="sec" :style="{ marginBottom: '6px' }"><span class="l"><span class="h-cn">关联工单</span><span class="h-en">LINK</span></span></div>
      <button type="button" class="rowline linkrow" @click="orderOpen = true">
        <span class="linktext">
          {{ linkedOrder ? `${linkedOrder.order_no} · ${linkedOrder.title.split(' · ')[0]}` : '不关联工单' }}
        </span>
        <BIcon name="chev" :size="12" class="chev" />
      </button>

      <div class="sec" :style="{ marginBottom: '6px' }">
        <span class="l"><span class="h-cn">问题描述</span><span class="h-en">DESC</span></span>
        <span class="all">{{ descLen }}/300</span>
      </div>
      <textarea v-model="form.content" class="desc" maxlength="300" placeholder="请描述具体情况（至少 10 个字），便于宿管核实处理" />
      <p v-if="descError" class="errtext">▲ {{ descError }}</p>

      <div class="sec" :style="{ marginBottom: '8px' }">
        <span class="l"><span class="h-cn">上传图片</span><span class="h-en">MEDIA</span></span>
        <span class="all">{{ form.media.length }}/4</span>
      </div>
      <PhotoUploader v-model="form.media" :max="4" biz-type="feedback" />

      <BButton :disabled="!canSubmit" :loading="submitting" @click="submit">提交反馈</BButton>

      <div class="sec"><span class="l"><span class="h-cn">我的反馈</span><span class="h-en">HISTORY</span></span></div>
      <div v-for="f in history" :key="f.id" class="fb">
        <div class="fbtop">
          <span class="fbno num-lg">{{ f.fb_no }} · {{ f.type_label }}</span>
          <BTag :text="statusOf(FEEDBACK_STATUS, f.status).label" :tone="statusOf(FEEDBACK_STATUS, f.status).tone === 'gray' ? 'gray' : 'ink'" sm />
        </div>
        <p class="fbcontent">{{ f.content }}</p>
        <div class="fbmeta">
          <span class="mini">{{ f.progress_text }}</span>
          <span class="mini">{{ f.created_text }}</span>
        </div>
        <div v-if="f.reply" class="reply">
          <span class="mini rlabel">宿管中心回复</span>
          <p>{{ f.reply }}</p>
          <div v-if="f.satisfaction" class="rated">
            <span class="mini">满意度</span>
            <StarRating :model-value="f.satisfaction" readonly :size="13" />
          </div>
          <button v-else-if="f.can_rate" type="button" class="btn-text ratebtn" @click="openRating(f)">评价处理结果 →</button>
        </div>
      </div>
      <p v-if="!history.length" class="mini empty">暂无反馈记录</p>

      <BSheet v-model="orderOpen" title="选择关联工单">
        <button v-for="o in orders" :key="o.id" type="button" class="orderopt" @click="form.order_id = o.id; orderOpen = false">
          <span class="ono num-lg">{{ o.order_no }}</span>
          <span class="ot">{{ o.title.split(' · ')[0] }}</span>
        </button>
        <p v-if="!orders.length" class="sheetdesc">暂无可关联的已完成工单</p>
        <template #footer>
          <BButton variant="ghost" @click="form.order_id = null; orderOpen = false">不关联工单</BButton>
        </template>
      </BSheet>

      <BSheet v-model="ratingOpen" title="评价处理结果">
        <p class="sheetdesc">你的评价将用于服务质量考核。</p>
        <div class="ratingrow">
          <StarRating v-model="ratingScore" :size="24" label="满意度" />
        </div>
        <template #footer>
          <BButton @click="rate">提交评价</BButton>
        </template>
      </BSheet>
    </div>
  </AppShell>
</template>

<style scoped>
.errtext {
  color: var(--red);
  font-size: 9px;
  letter-spacing: 0.06em;
  font-weight: 700;
  margin-top: 6px;
}
.linkrow {
  width: 100%;
  text-align: left;
}
.linktext {
  font-size: 12px;
  font-weight: 700;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chev {
  color: var(--ghost);
  flex: none;
}
.fb {
  padding: 12px 0;
  border-bottom: 1px solid var(--hair);
}
.fbtop {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.fbno {
  font-size: 11px;
  letter-spacing: 0.02em;
}
.fbcontent {
  font-size: 11.5px;
  line-height: 1.7;
  margin-top: 6px;
  color: #2a2a2a;
}
.fbmeta {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}
.reply {
  margin-top: 8px;
  background: var(--panel);
  padding: 10px 12px;
}
.rlabel {
  text-transform: none;
  letter-spacing: 0.02em;
  color: var(--red);
}
.reply p {
  font-size: 11px;
  line-height: 1.7;
  margin-top: 4px;
}
.rated {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}
.ratebtn {
  margin-top: 8px;
  font-size: 10px;
}
.empty {
  text-align: center;
  padding: 20px 0;
  text-transform: none;
}
.orderopt {
  display: flex;
  flex-direction: column;
  gap: 3px;
  width: 100%;
  text-align: left;
  padding: 11px 0;
  border-bottom: 1px solid var(--hair);
}
.ono {
  font-size: 11px;
  color: var(--mute);
}
.ot {
  font-size: 12.5px;
  font-weight: 700;
}
.sheetdesc {
  font-size: 11px;
  color: var(--mute);
  line-height: 1.7;
  margin: 8px 0 12px;
}
.ratingrow {
  display: flex;
  justify-content: center;
  padding: 10px 0 18px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}
</style>
