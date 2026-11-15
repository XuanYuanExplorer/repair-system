<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BIcon from '@/components/base/BIcon.vue'
import BButton from '@/components/base/BButton.vue'
import BField from '@/components/base/BField.vue'
import BSheet from '@/components/base/BSheet.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { profileApi } from '@/api/profile'
import { authApi } from '@/api/auth'
import { errText, isBizError } from '@/api/client'
import { useAsyncData } from '@/composables/useAsyncData'
import { useCountdown } from '@/composables/useCountdown'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { familyName } from '@/utils/format'
import { passwordStrength } from '@/utils/validate'
import type { DeviceItem } from '@/api/types'

const router = useRouter()
const ui = useUiStore()
const auth = useAuthStore()
const { data, loading, error, refresh } = useAsyncData('profile', profileApi.get)

const pwdOpen = ref(false)
const pwd = reactive({ old: '', next: '', confirm: '' })
const pwdError = ref('')
const pwdSaving = ref(false)

const phoneOpen = ref(false)
const phone = reactive({ new_phone: '', old_code: '', new_code: '' })
const phoneError = ref('')
const phoneSaving = ref(false)
const timer = useCountdown(0)

const devicesOpen = ref(false)
const devices = ref<DeviceItem[]>([])
const logoutOpen = ref(false)

onMounted(refresh)

async function openDevices() {
  devicesOpen.value = true
  try {
    devices.value = await authApi.devices()
  } catch (e) {
    ui.toast(errText(e, '设备列表加载失败'), 'red')
  }
}

async function revoke(id: number) {
  try {
    await authApi.revokeDevice(id)
    devices.value = devices.value.map((d) => (d.id === id ? { ...d, revoked: true } : d))
    ui.toast('该设备已下线')
  } catch (e) {
    ui.toast(errText(e, '操作失败'), 'red')
  }
}

async function changePassword() {
  pwdError.value = ''
  if (passwordStrength(pwd.next) === 'weak') {
    pwdError.value = '新密码需包含字母与数字，至少 6 位'
    return
  }
  if (pwd.next !== pwd.confirm) {
    pwdError.value = '两次输入不一致'
    return
  }
  pwdSaving.value = true
  try {
    await authApi.changePassword({ old_password: pwd.old, new_password: pwd.next })
    pwdOpen.value = false
    ui.toast('密码已修改，请重新登录')
    await auth.logout()
    await router.replace('/login')
  } catch (e) {
    if (isBizError(e) && e.code === 2004) pwdError.value = '新密码不能与最近 3 次使用过的密码重复'
    else pwdError.value = errText(e, '修改失败')
  } finally {
    pwdSaving.value = false
  }
}

async function sendCode(scene: 'old' | 'new') {
  if (timer.active.value) return
  try {
    const target = scene === 'new' ? phone.new_phone : (data.value?.phone || '')
    const res = await authApi.smsCode(target, 'bind')
    timer.start(res.retry_after || 60)
    ui.toast(res.debug_code ? `验证码已发送（开发环境：${res.debug_code}）` : '验证码已发送')
  } catch (e) {
    ui.toast(errText(e, '发送失败'), 'red')
  }
}

async function rebind() {
  phoneError.value = ''
  phoneSaving.value = true
  try {
    await authApi.rebindPhone(phone)
    phoneOpen.value = false
    ui.toast('手机号已换绑')
    await refresh(true)
  } catch (e) {
    phoneError.value = errText(e, '换绑失败')
  } finally {
    phoneSaving.value = false
  }
}

async function doLogout() {
  logoutOpen.value = false
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <AppShell tab="profile">
    <div class="page">
      <div class="k-brand">PROFILE</div>

      <SkeletonList v-if="loading && !data" :rows="3" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <div class="hero">
          <span class="avatar big">{{ familyName(data.name) }}</span>
          <div class="heroinfo">
            <b class="name">{{ data.name }}</b>
            <span class="mini sub">{{ data.subtitle }}</span>
          </div>
          <button type="button" class="editbtn" @click="router.push('/profile/edit')">
            编辑资料 <BIcon name="chev" :size="11" />
          </button>
        </div>

        <div class="sec">
          <span class="l"><span class="h-cn">认证信息</span><span class="h-en">VERIFIED</span></span>
          <BIcon name="lock" :size="12" class="lock" />
        </div>
        <div class="rowline"><span class="k">学号</span><span class="num-lg ro">{{ data.verified.student_no }}</span></div>
        <div class="rowline"><span class="k">学院 / 班级</span><span class="ro">{{ data.verified.college_class }}</span></div>
        <div class="rowline"><span class="k">宿舍 / 床位</span><span class="ro">{{ data.verified.dorm }}</span></div>

        <div class="sec"><span class="l"><span class="h-cn">账号与安全</span><span class="h-en">SECURITY</span></span></div>
        <button type="button" class="srow" @click="pwdOpen = true">
          <span class="sname"><BIcon name="key" :size="15" />修改密码</span>
          <BIcon name="chev" :size="12" class="chev" />
        </button>
        <button type="button" class="srow" @click="phoneOpen = true">
          <span class="sname"><BIcon name="phone" :size="15" />换绑手机号<span class="ssub">{{ data.security.phone }}</span></span>
          <BIcon name="chev" :size="12" class="chev" />
        </button>
        <button type="button" class="srow" @click="openDevices">
          <span class="sname"><BIcon name="shield" :size="15" />登录设备与安全记录</span>
          <span class="scount">{{ data.security.device_count }}</span>
          <BIcon name="chev" :size="12" class="chev" />
        </button>
        <div class="srow static">
          <span class="sname"><BIcon name="user" :size="15" />紧急联系人<span class="ssub">{{ data.security.emergency_text }}</span></span>
        </div>

        <button type="button" class="logout" @click="logoutOpen = true">退出登录</button>

        <p class="foot">{{ data.version }} · 江南大学智慧宿管中心</p>
      </template>

      <BSheet v-model="pwdOpen" title="修改密码">
        <BField v-model="pwd.old" label="当前密码" type="password" placeholder="请输入当前密码" autocomplete="current-password" />
        <BField v-model="pwd.next" label="新密码" type="password" placeholder="字母 + 数字，至少 6 位" autocomplete="new-password" />
        <BField v-model="pwd.confirm" label="确认密码" type="password" placeholder="再次输入新密码" autocomplete="new-password" />
        <p v-if="pwdError" class="sheetdesc red">▲ {{ pwdError }}</p>
        <template #footer>
          <BButton :loading="pwdSaving" @click="changePassword">确认修改</BButton>
        </template>
      </BSheet>

      <BSheet v-model="phoneOpen" title="换绑手机号">
        <BField v-model="phone.new_phone" label="新手机号" inputmode="tel" :maxlength="11" placeholder="11 位手机号" />
        <BField v-model="phone.old_code" label="原手机验证码" inputmode="numeric" :maxlength="6">
          <template #suffix>
            <button type="button" class="send" @click="sendCode('old')">发送</button>
          </template>
        </BField>
        <BField v-model="phone.new_code" label="新手机验证码" inputmode="numeric" :maxlength="6">
          <template #suffix>
            <button type="button" class="send" @click="sendCode('new')">发送</button>
          </template>
        </BField>
        <p v-if="timer.active.value" class="sheetdesc">验证码已发送，{{ timer.text.value }} 后可重新获取</p>
        <p v-if="phoneError" class="sheetdesc red">▲ {{ phoneError }}</p>
        <template #footer>
          <BButton :loading="phoneSaving" @click="rebind">确认换绑</BButton>
        </template>
      </BSheet>

      <BSheet v-model="devicesOpen" title="登录设备与安全记录">
        <div v-for="d in devices" :key="d.id" class="devrow">
          <div>
            <b>{{ d.device_name }}</b>
            <span class="mini devsub">{{ d.ip }} · {{ (d.last_active_at || '').replace('T', ' ').slice(5, 16) }}</span>
          </div>
          <span v-if="d.revoked" class="mini">已下线</span>
          <button v-else type="button" class="btn-text revoke" @click="revoke(d.id)">下线</button>
        </div>
        <p v-if="!devices.length" class="sheetdesc">暂无登录记录</p>
        <template #footer>
          <BButton variant="ghost" @click="devicesOpen = false">关闭</BButton>
        </template>
      </BSheet>

      <BSheet v-model="logoutOpen" title="退出登录">
        <p class="sheetdesc">退出后需重新输入学号与密码登录，本机缓存的登录状态将被清除。</p>
        <template #footer>
          <BButton variant="ghost-red" @click="doLogout">确认退出</BButton>
        </template>
      </BSheet>
    </div>
  </AppShell>
</template>

<style scoped>
.hero {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-top: 8px;
}
.big {
  width: 60px;
  height: 60px;
  font-size: 24px;
}
.heroinfo {
  flex: 1;
  min-width: 0;
}
.name {
  font-size: 18px;
}
.sub {
  display: block;
  margin-top: 4px;
  text-transform: none;
  letter-spacing: 0.02em;
}
.editbtn {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--hair);
  padding: 6px 8px;
  flex: none;
}
.lock {
  color: var(--mute);
  opacity: 0.6;
}
.k {
  font-size: 11.5px;
  color: var(--mute);
}
.ro {
  font-size: 12px;
  font-weight: 700;
  color: #5a5a58;
}
.srow {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 13px 0;
  border-bottom: 1px solid var(--hair);
  text-align: left;
}
.srow.static {
  border-bottom: none;
}
.sname {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
  font-weight: 700;
  flex: 1;
  flex-wrap: wrap;
}
.ssub {
  font-size: 9.5px;
  color: var(--mute);
  font-weight: 600;
  width: 100%;
  padding-left: 24px;
  margin-top: 2px;
}
.scount {
  font-family: var(--serif);
  font-size: 13px;
  font-weight: 700;
  color: var(--mute);
}
.chev {
  color: var(--ghost);
  flex: none;
}
.logout {
  width: 100%;
  text-align: center;
  color: var(--red);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.1em;
  padding: 18px 0;
  margin-top: 10px;
}
.foot {
  text-align: center;
  font-size: 9px;
  color: var(--ghost);
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.sheetdesc {
  font-size: 11px;
  color: var(--mute);
  line-height: 1.7;
  margin: 8px 0 12px;
}
.send {
  font-size: 10px;
  font-weight: 800;
  color: var(--red);
  flex: none;
  white-space: nowrap;
  padding: 4px 0 4px 8px;
}
.devrow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--hair);
  font-size: 12px;
}
.devsub {
  display: block;
  margin-top: 3px;
  text-transform: none;
  letter-spacing: 0.02em;
}
.revoke {
  font-size: 10px;
}

/* ---------- 桌面：阅读宽度约束（页面已由全局响应式放大字号/间距） ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: none;
  }
}
</style>
