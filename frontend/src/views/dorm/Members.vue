<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import MemberRow from '@/components/data/MemberRow.vue'
import BButton from '@/components/base/BButton.vue'
import BSheet from '@/components/base/BSheet.vue'
import BTag from '@/components/base/BTag.vue'
import BIcon from '@/components/base/BIcon.vue'
import BChip from '@/components/base/BChip.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { dormApi } from '@/api/dorm'
import { errText } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import type { AssetItem } from '@/api/types'

const ui = useUiStore()
const members = useAsyncData('dorm:members', dormApi.members)
const rules = useAsyncData('dorm:rules', dormApi.rules)
const assets = ref<AssetItem[]>([])

const rulesOpen = ref(false)
const rulesDraft = ref<string[]>([])
const saving = ref(false)
const changeOpen = ref(false)
const change = reactive({ req_type: 'checkin' as 'checkin' | 'checkout' | 'swap', target_room: '', reason: '' })
const submitting = ref(false)

const CHANGE_TYPES = [
  { value: 'checkin', label: '入住申请' },
  { value: 'checkout', label: '退宿申请' },
  { value: 'swap', label: '调宿申请' },
]

async function loadAssets() {
  try {
    assets.value = await dormApi.assets()
  } catch {
    // 物品清单失败静默
  }
}

onMounted(loadAssets)

function openRules() {
  rulesDraft.value = (rules.data.value?.items || []).map((r) => r.content)
  if (!rulesDraft.value.length) rulesDraft.value = ['']
  rulesOpen.value = true
}

function addRule() {
  if (rulesDraft.value.length >= 8) {
    ui.toast('最多 8 条公约', 'red')
    return
  }
  rulesDraft.value = [...rulesDraft.value, '']
}

function removeRule(i: number) {
  rulesDraft.value = rulesDraft.value.filter((_, idx) => idx !== i)
}

function move(i: number, dir: -1 | 1) {
  const next = [...rulesDraft.value]
  const j = i + dir
  if (j < 0 || j >= next.length) return
  ;[next[i], next[j]] = [next[j], next[i]]
  rulesDraft.value = next
}

async function saveRules() {
  const items = rulesDraft.value.map((s) => s.trim()).filter(Boolean)
  if (!items.length) {
    ui.toast('公约内容不能为空', 'red')
    return
  }
  saving.value = true
  try {
    await dormApi.saveRules(items)
    rulesOpen.value = false
    ui.toast('寝室公约已更新')
    await rules.refresh(true)
  } catch (e) {
    ui.toast(errText(e, '保存失败'), 'red')
  } finally {
    saving.value = false
  }
}

async function toggleAsset(a: AssetItem) {
  if (!members.data.value?.can_edit) {
    ui.toast('仅寝室长可登记物品借还', 'red')
    return
  }
  try {
    if (a.status === 'available') await dormApi.borrowAsset(a.id)
    else if (a.holder_is_me) await dormApi.returnAsset(a.id)
    else {
      ui.toast(`当前由 ${a.holder_name} 借用`, 'red')
      return
    }
    ui.toast(a.status === 'available' ? '已登记借用' : '已归还')
    await loadAssets()
  } catch (e) {
    ui.toast(errText(e, '操作失败'), 'red')
  }
}

async function submitChange() {
  submitting.value = true
  try {
    await dormApi.createRoomChange({
      req_type: change.req_type,
      target_room: change.req_type === 'swap' ? change.target_room : undefined,
      reason: change.reason || undefined,
    })
    changeOpen.value = false
    change.reason = ''
    change.target_room = ''
    ui.toast('申请已提交，等待宿管审批')
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
        kicker="MEMBERS"
        title="寝室成员"
        :subtitle="members.data.value ? `${members.data.value.room} · 普通成员进入为只读视图` : undefined"
        back
        @back="$router.back()"
      >
        <template #right>
          <BTag v-if="members.data.value?.can_edit" tone="red" text="寝室长权限" />
        </template>
      </PageHeader>

      <SkeletonList v-if="members.loading.value && !members.data.value" :rows="4" variant="row" />
      <ErrorRetry v-else-if="members.error.value" :message="members.error.value" @retry="members.refresh()" />

      <template v-else-if="members.data.value">
        <div class="sec">
          <span class="l"><span class="h-cn">成员名单 / 床位</span><span class="h-en">ROSTER</span></span>
          <span class="all">{{ members.data.value.occupied }}/{{ members.data.value.capacity }}</span>
        </div>
        <MemberRow v-for="(m, i) in members.data.value.items" :key="m.bed_no" :member="m" :index="i + 1" />

        <div class="sec">
          <span class="l"><span class="h-cn">公共物品领用</span><span class="h-en">ASSETS</span></span>
          <span class="all">{{ assets.length }} 项</span>
        </div>
        <button v-for="a in assets" :key="a.id" type="button" class="asset" @click="toggleAsset(a)">
          <span class="aname">
            <BIcon name="clip" :size="15" />
            <span>
              {{ a.name }}
              <span class="asub" :class="{ red: a.status === 'borrowed' && !a.returned_at }">{{ a.text }}</span>
            </span>
          </span>
          <span class="aact">{{ a.status === 'available' ? '登记借用' : a.holder_is_me ? '归还' : '不可操作' }}</span>
        </button>

        <div class="sec"><span class="l"><span class="h-cn">本寝公约</span><span class="h-en">RULES</span></span></div>
        <ol class="rules">
          <li v-for="(r, i) in rules.data.value?.items || []" :key="i">
            <span class="idx num-lg">{{ String(i + 1).padStart(2, '0') }}</span>
            <span>{{ r.content }}</span>
          </li>
          <li v-if="!rules.data.value?.items?.length" class="mute empty">寝室长尚未维护公约</li>
        </ol>

        <div class="spacer" />
        <div class="btn-row">
          <BButton variant="ghost" @click="changeOpen = true">提交入住 / 退宿申请</BButton>
          <BButton v-if="members.data.value.can_edit" @click="openRules">编辑公约</BButton>
        </div>
      </template>

      <!-- 公约编辑 -->
      <BSheet v-model="rulesOpen" title="编辑寝室公约" height="76vh">
        <p class="sheetdesc">最多 8 条，每条不超过 200 字；保存后整表覆盖，所有成员可见。</p>
        <div v-for="(r, i) in rulesDraft" :key="i" class="ruleedit">
          <span class="ridx num-lg">{{ String(i + 1).padStart(2, '0') }}</span>
          <textarea v-model="rulesDraft[i]" class="rinput" rows="2" maxlength="200" placeholder="例如：23:00 后保持安静，熄灯就寝" />
          <div class="rops">
            <button type="button" aria-label="上移" :disabled="i === 0" @click="move(i, -1)">↑</button>
            <button type="button" aria-label="下移" :disabled="i === rulesDraft.length - 1" @click="move(i, 1)">↓</button>
            <button type="button" aria-label="删除" @click="removeRule(i)">✕</button>
          </div>
        </div>
        <button type="button" class="btn ghost sm addrule" @click="addRule">＋ 添加一条</button>
        <template #footer>
          <BButton :loading="saving" @click="saveRules">保存公约</BButton>
        </template>
      </BSheet>

      <!-- 入住 / 退宿 / 调宿申请 -->
      <BSheet v-model="changeOpen" title="提交住宿申请">
        <div class="chips">
          <BChip v-for="t in CHANGE_TYPES" :key="t.value" :on="change.req_type === t.value" @click="change.req_type = t.value as typeof change.req_type">
            {{ t.label }}
          </BChip>
        </div>
        <div v-if="change.req_type === 'swap'" class="targetrow">
          <span class="mini">期望寝室</span>
          <input v-model="change.target_room" class="targetinput" maxlength="20" placeholder="例如 3号楼 508 室" />
        </div>
        <div class="reasonrow">
          <span class="mini">申请理由</span>
        </div>
        <textarea v-model="change.reason" class="desc" maxlength="300" placeholder="请说明申请原因（选填）" />
        <template #footer>
          <BButton :loading="submitting" @click="submitChange">提交申请</BButton>
        </template>
      </BSheet>
    </div>
  </AppShell>
</template>

<style scoped>
.asset {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 0;
  border-bottom: 1px solid var(--hair);
  text-align: left;
}
.aname {
  display: flex;
  gap: 9px;
  align-items: flex-start;
  font-size: 12.5px;
  font-weight: 700;
}
.asub {
  display: block;
  font-size: 9.5px;
  color: var(--mute);
  font-weight: 600;
  margin-top: 2px;
}
.aact {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--mute);
  flex: none;
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
.sheetdesc {
  font-size: 10.5px;
  color: var(--mute);
  line-height: 1.7;
  margin: 6px 0 12px;
}
.ruleedit {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--hair);
}
.ridx {
  font-size: 10px;
  color: var(--mute);
  padding-top: 8px;
  flex: none;
}
.rinput {
  flex: 1;
  border: 1px solid var(--hair);
  background: var(--panel);
  padding: 8px 10px;
  font-size: 11.5px;
  line-height: 1.6;
  resize: none;
}
.rops {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: none;
}
.rops button {
  width: 20px;
  height: 18px;
  font-size: 10px;
  color: var(--mute);
  border: 1px solid var(--hair);
}
.rops button:disabled {
  opacity: 0.3;
}
.addrule {
  margin-top: 12px;
}
.targetrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: var(--line) solid var(--ink);
}
.targetinput {
  flex: 1;
  text-align: right;
  font-size: 12px;
  font-weight: 700;
}
.reasonrow {
  margin-top: 12px;
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
