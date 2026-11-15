<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BField from '@/components/base/BField.vue'
import BButton from '@/components/base/BButton.vue'
import BIcon from '@/components/base/BIcon.vue'
import BChip from '@/components/base/BChip.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { profileApi } from '@/api/profile'
import { fileApi } from '@/api/files'
import { errText } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { familyName } from '@/utils/format'
import { isEmail, isPhone } from '@/utils/validate'

const router = useRouter()
const ui = useUiStore()
const auth = useAuthStore()
const { data, loading, error, refresh } = useAsyncData('profile', profileApi.get)

const form = reactive({ avatar_url: '', gender: 1, emergency_name: '', emergency_phone: '', email: '' })
const errors = reactive<Record<string, string>>({})
const saving = ref(false)
const uploading = ref(false)

const GENDER = [
  { value: 1, label: '男' },
  { value: 2, label: '女' },
  { value: 0, label: '不公开' },
]

const avatarText = computed(() => (data.value ? familyName(data.value.name) : '?'))

onMounted(async () => {
  await refresh()
  if (data.value) {
    form.avatar_url = data.value.avatar_url || ''
    form.gender = data.value.gender ?? 1
    form.emergency_name = data.value.emergency_name || ''
    form.emergency_phone = data.value.emergency_phone || ''
    form.email = data.value.email || ''
  }
})

async function onAvatar(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    const res = await fileApi.upload(file, 'avatar')
    form.avatar_url = res.url
    ui.toast('头像已上传')
  } catch (err) {
    ui.toast(errText(err, '上传失败'), 'red')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function validate(): boolean {
  errors.emergency_name = form.emergency_name && form.emergency_name.length < 2 ? '请填写联系人姓名' : ''
  errors.emergency_phone = form.emergency_phone && !isPhone(form.emergency_phone) ? '手机号格式有误' : ''
  errors.email = form.email && !isEmail(form.email) ? '邮箱格式有误' : ''
  return !Object.values(errors).some(Boolean)
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    // 学号 / 姓名 / 宿舍为只读字段，不随提交发送（后端同样拒绝）
    const res = await profileApi.update({
      avatar_url: form.avatar_url || null,
      gender: form.gender,
      emergency_name: form.emergency_name || undefined,
      emergency_phone: form.emergency_phone || undefined,
      email: form.email || undefined,
    })
    auth.patchUser({ avatar_url: res.avatar_url, phone: res.phone })
    ui.toast('资料已保存')
    await router.back()
  } catch (e) {
    ui.toast(errText(e, '保存失败'), 'red')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="EDIT PROFILE" title="编辑资料" subtitle="学号、姓名与床位由宿管系统同步，不可修改" back @back="router.back()" />

      <SkeletonList v-if="loading && !data" :rows="3" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <div class="avatarrow">
          <label class="avatarwrap">
            <img v-if="form.avatar_url" :src="form.avatar_url" alt="头像" />
            <span v-else class="avatar">{{ avatarText }}</span>
            <span class="cam"><BIcon name="cam" :size="13" /></span>
            <input type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onAvatar" />
          </label>
          <div class="avatarhint">
            <b>{{ uploading ? '上传中…' : '点击更换头像' }}</b>
            <span class="mini">支持 JPG / PNG，建议 1:1</span>
          </div>
        </div>

        <div class="sec"><span class="l"><span class="h-cn">只读信息</span><span class="h-en">READ ONLY</span></span></div>
        <div class="rowline"><span class="k">学号 <BIcon name="lock" :size="11" /></span><span class="ro num-lg">{{ data.student_no }}</span></div>
        <div class="rowline"><span class="k">姓名 <BIcon name="lock" :size="11" /></span><span class="ro">{{ data.name }}</span></div>
        <div class="rowline"><span class="k">宿舍 <BIcon name="lock" :size="11" /></span><span class="ro">{{ data.verified.dorm }}</span></div>

        <div class="sec"><span class="l"><span class="h-cn">可编辑信息</span><span class="h-en">EDITABLE</span></span></div>
        <div class="genderrow">
          <span class="k">性别</span>
          <div class="chips">
            <BChip v-for="g in GENDER" :key="g.value" :on="form.gender === g.value" @click="form.gender = g.value">{{ g.label }}</BChip>
          </div>
        </div>

        <BField v-model="form.emergency_name" label="紧急联系人" placeholder="如 林父" :maxlength="20" :error="errors.emergency_name" />
        <BField v-model="form.emergency_phone" label="联系人电话" placeholder="11 位手机号" inputmode="tel" :maxlength="11" :error="errors.emergency_phone" />
        <BField v-model="form.email" label="邮箱" placeholder="用于接收电子票据" inputmode="email" :maxlength="100" :error="errors.email" />

        <div class="spacer" />
        <BButton :loading="saving" @click="save">保存资料</BButton>
        <p class="hint">如学号、姓名或床位有误，请联系宿管中心 0510-8818 6112 更正</p>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.avatarrow {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 20px;
}
.avatarwrap {
  position: relative;
  flex: none;
  cursor: pointer;
}
.avatarwrap img,
.avatarwrap .avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
}
.cam {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 22px;
  height: 22px;
  background: var(--ink);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatarhint {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.avatarhint .mini {
  text-transform: none;
  letter-spacing: 0.02em;
}
.k {
  font-size: 11.5px;
  color: var(--mute);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.ro {
  font-size: 12px;
  font-weight: 700;
  color: #5a5a58;
}
.genderrow {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
  border-bottom: var(--line) solid var(--ink);
}
.hint {
  font-size: 9px;
  color: var(--mute);
  text-align: center;
  margin-top: 10px;
  line-height: 1.7;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}
</style>
