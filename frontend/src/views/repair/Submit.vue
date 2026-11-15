<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BChip from '@/components/base/BChip.vue'
import BSwitch from '@/components/base/BSwitch.vue'
import BField from '@/components/base/BField.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import BSegTabs from '@/components/base/BSegTabs.vue'
import BIcon from '@/components/base/BIcon.vue'
import PhotoUploader from '@/components/form/PhotoUploader.vue'
import SlotPicker from '@/components/form/SlotPicker.vue'
import { repairApi } from '@/api/repair'
import { errText, isBizError } from '@/api/client'
import { CATEGORY_LIST, PUBLIC_AREAS, ROOM_SPOTS } from '@/utils/dict'
import { charLen, isPhone } from '@/utils/validate'
import { fmtDate, uuid } from '@/utils/format'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import type { SlotItem } from '@/api/types'

const router = useRouter()
const route = useRoute()
const ui = useUiStore()
const auth = useAuthStore()

const today = fmtDate(new Date())
const tomorrow = fmtDate(new Date(Date.now() + 86400000))

const form = reactive({
  category: 'ac',
  locationType: 'in_room' as 'in_room' | 'public',
  spot: ROOM_SPOTS[0],
  area: PUBLIC_AREAS[0],
  description: '',
  media: [] as string[],
  date: today,
  slot: '',
  presence: true,
  phone: auth.user?.phone || '',
})

const dateTabs = [
  { value: today, label: '今天' },
  { value: tomorrow, label: '明天' },
]
const slots = ref<SlotItem[]>([])
const slotLoading = ref(false)
const editingPhone = ref(false)
const phoneError = ref('')
const submitting = ref(false)
const sheetOpen = ref(false)
const errors = reactive<{ category: string; description: string; slot: string }>({ category: '', description: '', slot: '' })

const roomText = computed(() => auth.user?.room || '本寝')
const locationText = computed(() =>
  form.locationType === 'public' ? `公共区域 — ${form.area}` : `${roomText.value} · 室内 — ${form.spot}`,
)
const descLen = computed(() => charLen(form.description))
const canSubmit = computed(() => !!form.category && form.description.trim().length >= 10 && !!form.slot && !submitting.value)

async function loadSlots() {
  slotLoading.value = true
  try {
    const res = await repairApi.slots(form.date)
    slots.value = res.items
    if (form.slot && res.items.find((s) => s.code === form.slot)?.full) form.slot = ''
  } catch (e) {
    ui.toast(errText(e, '时段加载失败'), 'red')
  } finally {
    slotLoading.value = false
  }
}

onMounted(() => {
  // 从设施清单进入：带类别 / 位置 / 预填描述
  const q = route.query
  if (typeof q.category === 'string' && CATEGORY_LIST.some((c) => c.value === q.category)) form.category = q.category
  if (typeof q.spot === 'string' && q.spot) form.spot = q.spot
  if (q.category === 'public') form.locationType = 'public'
  if (typeof q.desc === 'string' && q.desc) form.description = q.desc
  void loadSlots()
})

watch(
  () => form.date,
  () => loadSlots(),
)

watch(
  () => form.category,
  (v) => {
    form.locationType = v === 'public' ? 'public' : 'in_room'
    if (v === 'public') form.spot = ROOM_SPOTS[0]
  },
)

function beforeSubmit() {
  errors.category = form.category ? '' : '请选择报修类别'
  errors.description = charLen(form.description.trim()) >= 10 ? '' : '请至少填写 10 个字，便于师傅提前备件'
  errors.slot = form.slot ? '' : '请选择期望上门时段'
  if (form.phone && !isPhone(form.phone)) {
    phoneError.value = '请输入 11 位手机号'
    editingPhone.value = true
    return
  }
  if (errors.category || errors.description || errors.slot) return
  sheetOpen.value = true
}

async function submit() {
  if (submitting.value) return
  submitting.value = true
  const idem = uuid()
  try {
    const res = await repairApi.create(
      {
        category: form.category,
        location_type: form.locationType,
        location_desc: locationText.value.slice(0, 100),
        description: form.description.trim(),
        media_urls: form.media,
        preferred_date: form.date,
        preferred_slot: form.slot,
        require_presence: form.presence,
        contact_phone: form.phone,
        client_request_id: idem,
      },
      idem,
    )
    sheetOpen.value = false
    ui.toast(`工单已提交 ${res.order_no}`)
    await router.replace(`/repair/${res.id}`)
  } catch (e) {
    sheetOpen.value = false
    if (isBizError(e) && (e.code === 3002 || e.code === 3001)) {
      await loadSlots()
      form.slot = ''
      errors.slot = e.message
      window.scrollTo({ top: 240, behavior: 'smooth' })
    } else if (isBizError(e) && e.code === 3004) {
      ui.toast('照片数量超限，请删除后重试', 'red')
    } else {
      ui.toast(errText(e, '提交失败，请稍后重试'), 'red')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="REPAIR / 提交工单" title="报修提交" />

      <div class="sec"><span class="l"><span class="h-cn">报修类别</span><span class="h-en">TYPE</span></span></div>
      <div class="chips">
        <BChip v-for="c in CATEGORY_LIST" :key="c.value" :on="form.category === c.value" @click="form.category = c.value">{{ c.label }}</BChip>
      </div>
      <p v-if="errors.category" class="errtext">▲ {{ errors.category }}</p>

      <div class="sec" :style="{ marginBottom: '6px' }">
        <span class="l"><span class="h-cn">故障位置</span><span class="h-en">SPOT</span></span>
      </div>
      <div class="rowline loc">
        <span class="loctext">{{ locationText }}</span>
        <select v-if="form.locationType === 'in_room'" v-model="form.spot" class="picker" aria-label="房间内位置">
          <option v-for="s in ROOM_SPOTS" :key="s" :value="s">{{ s }}</option>
        </select>
        <select v-else v-model="form.area" class="picker" aria-label="公共区域">
          <option v-for="a in PUBLIC_AREAS" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>

      <div class="sec" :style="{ marginBottom: '6px' }">
        <span class="l"><span class="h-cn">故障描述</span><span class="h-en">DESC</span></span>
        <span class="all" :class="{ red: descLen > 200 }">{{ descLen }}/200</span>
      </div>
      <textarea
        v-model="form.description"
        class="desc"
        maxlength="200"
        placeholder="请描述故障现象、出现时间，是否已尝试处理（至少 10 个字）"
      />
      <p v-if="errors.description" class="errtext">▲ {{ errors.description }}</p>

      <div class="sec" :style="{ marginBottom: '8px' }">
        <span class="l"><span class="h-cn">现场照片 / 视频</span><span class="h-en">MEDIA</span></span>
        <span class="all">{{ form.media.length }}/6</span>
      </div>
      <PhotoUploader v-model="form.media" :max="6" biz-type="repair" />

      <div class="sec" :style="{ marginBottom: '6px' }">
        <span class="l"><span class="h-cn">期望上门时段</span><span class="h-en">SLOT</span></span>
      </div>
      <BSegTabs v-model="form.date" :items="dateTabs" class="daytabs" />
      <SlotPicker v-model="form.slot" :slots="slots" :loading="slotLoading" />
      <p v-if="errors.slot" class="errtext">▲ {{ errors.slot }}</p>

      <div class="rowline switchrow">
        <span class="switchlabel">本人在场</span>
        <BSwitch v-model="form.presence" label="本人在场" />
      </div>

      <BField
        v-if="editingPhone"
        v-model="form.phone"
        label="联系电话"
        inputmode="tel"
        :maxlength="11"
        :error="phoneError"
        placeholder="11 位手机号"
      />
      <div v-else class="rowline switchrow">
        <span class="switchlabel">联系电话</span>
        <span class="phonetext">{{ form.phone }}</span>
        <button type="button" class="btn-text ink change" @click="editingPhone = true; form.phone = ''">修改</button>
      </div>

      <div class="spacer" />
      <BButton :disabled="!canSubmit" @click="beforeSubmit">确认信息 · 提交工单</BButton>

      <BSheet v-model="sheetOpen" title="提交前确认">
        <div class="sheetrow"><span>类别</span><b>{{ CATEGORY_LIST.find((c) => c.value === form.category)?.label }}</b></div>
        <div class="sheetrow"><span>位置</span><b>{{ locationText }}</b></div>
        <div class="sheetrow"><span>时段</span><b>{{ slots.find((s) => s.code === form.slot)?.label || form.slot }}</b></div>
        <div class="sheetrow"><span>照片</span><b>{{ form.media.length }} 张</b></div>
        <div class="sheetrow"><span>联系电话</span><b>{{ form.phone }}</b></div>
        <div class="sheetrow"><span>本人在场</span><b>{{ form.presence ? '是' : '否，可授权入内' }}</b></div>
        <p class="sheetnote">提交后宿管中心将尽快受理，可在“我的报修”查看进度。</p>
        <template #footer>
          <BButton :loading="submitting" @click="submit">
            <BIcon name="check" :size="15" />确认提交
          </BButton>
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
.loc {
  gap: 8px;
}
.loctext {
  font-size: 12px;
  font-weight: 700;
  flex: 1;
  min-width: 0;
}
.picker {
  width: auto;
  max-width: 96px;
  font-size: 10px;
  font-weight: 700;
  color: var(--mute);
  letter-spacing: 0.02em;
  text-align: right;
  flex: none;
}
.desc {
  width: 100%;
}
.daytabs {
  margin-bottom: 6px;
}
.daytabs :deep(button) {
  padding: 7px 0;
  font-size: 10px;
}
.switchrow {
  padding: 12px 0;
}
.switchlabel {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.phonetext {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.change {
  margin-left: 10px;
}
.sheetrow {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--hair);
  font-size: 11.5px;
}
.sheetrow span {
  color: var(--mute);
  font-size: 10px;
  letter-spacing: 0.1em;
}
.sheetrow b {
  text-align: right;
  font-weight: 700;
}
.sheetnote {
  font-size: 10px;
  color: var(--mute);
  line-height: 1.7;
  margin-top: 10px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}
</style>
