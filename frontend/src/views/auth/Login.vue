<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import BField from '@/components/base/BField.vue'
import BCheckbox from '@/components/base/BCheckbox.vue'
import BButton from '@/components/base/BButton.vue'
import BIcon from '@/components/base/BIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { useBadgeStore } from '@/stores/badge'
import { useUiStore } from '@/stores/ui'
import { authApi } from '@/api/auth'
import { homeApi } from '@/api/home'
import { isBizError } from '@/api/client'
import { useCountdown } from '@/composables/useCountdown'
import type { PublicNotice } from '@/api/types'

const auth = useAuthStore()
const badge = useBadgeStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ account: '20223601', password: 'Abc123456', remember: true })
const showPwd = ref(false)
const submitting = ref(false)
const formError = ref('')
const notice = ref<PublicNotice | null>(null)
const school = ref('江南大学 · 智慧宿管中心')
const lock = useCountdown(0)

onMounted(async () => {
  try {
    const [notices, meta] = await Promise.all([homeApi.latestNotices(), homeApi.meta()])
    notice.value = notices?.[0] ?? null
    if (meta?.school) school.value = meta.school
  } catch {
    // 公告/元信息失败不影响登录
  }
})

function validate(): boolean {
  if (!form.account.trim()) {
    formError.value = '请输入学号或手机号'
    return false
  }
  if (form.password.length < 6) {
    formError.value = '密码至少 6 位'
    return false
  }
  formError.value = ''
  return true
}

async function submit() {
  if (submitting.value || lock.active.value) return
  if (!validate()) return
  submitting.value = true
  try {
    await auth.login(form.account.trim(), form.password, form.remember)
    // 预取聚合数据，不阻塞跳转
    homeApi.summary().then((s) => badge.fromSummary(s)).catch(() => {})
    ui.toast(`欢迎回来，${auth.displayName}`)
    const redirect = route.query.redirect
    const target = typeof redirect === 'string' && redirect.startsWith('/') ? redirect : '/'
    await router.replace(target)
  } catch (e) {
    if (isBizError(e) && e.code === 2006) {
      const retry = Number((e.data as { retry_after?: number } | null)?.retry_after ?? 900)
      lock.start(retry)
      formError.value = `账号已锁定，请 ${Math.ceil(retry / 60)} 分钟后重试`
    } else if (isBizError(e)) {
      formError.value = e.message || '账号或密码错误'
      if (e.code === 2005) form.password = ''
    } else {
      formError.value = '网络异常，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page login">
      <div class="k-brand brand">DORM SERVICE</div>
      <h1 class="big headline">登录<br />宿舍服务平台</h1>
      <p class="mini school">{{ school }}</p>

      <div class="fields">
        <BField v-model="form.account" label="学号/手机" placeholder="请输入学号或手机号" inputmode="text" @enter="submit" />
        <BField
          v-model="form.password"
          label="密码"
          :type="showPwd ? 'text' : 'password'"
          placeholder="请输入密码"
          :suffix="showPwd ? 'HIDE' : 'SHOW'"
          autocomplete="current-password"
          @suffix="showPwd = !showPwd"
          @enter="submit"
        />
      </div>

      <p v-if="formError" class="formerr">▲ {{ formError }}</p>
      <p v-if="lock.active.value" class="formerr">▲ 账号已锁定，{{ lock.text.value }} 后可重试</p>

      <div class="options">
        <label class="remember">
          <BCheckbox v-model="form.remember" />
          <span>记住登录状态</span>
        </label>
        <RouterLink to="/reset" class="forgot">忘记密码？</RouterLink>
      </div>

      <BButton :loading="submitting" :disabled="lock.active.value" @click="submit">登 录 · LOG IN</BButton>

      <div class="or"><span /><em>OR</em><span /></div>

      <BButton variant="ghost" @click="ui.toast('微信扫码登录即将开放')">
        <BIcon name="shield" :size="15" />微信 / 企业微信扫码登录
      </BButton>

      <p class="register">还没有账号？<RouterLink to="/register" class="red b">立即注册 →</RouterLink></p>

      <div v-if="notice" class="notice bottom">
        公告 · {{ notice.title }}<template v-if="notice.date">（{{ notice.date }}）</template>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.login {
  min-height: 100%;
}
.brand {
  margin-top: 22px;
}
.headline {
  font-size: 36px;
  line-height: 1.15;
}
.school {
  margin-top: 8px;
  text-transform: none;
  letter-spacing: 0.04em;
}
.fields {
  margin-top: 30px;
}
.formerr {
  font-size: 10px;
  color: var(--red);
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-top: 10px;
  line-height: 1.6;
}
.options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}
.remember {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  cursor: pointer;
}
.forgot {
  font-size: 11px;
  font-weight: 700;
}
.or {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
  font-size: 9px;
  letter-spacing: 0.2em;
  color: var(--mute);
  font-weight: 700;
}
.or span {
  flex: 1;
  border-top: 1px solid var(--hair);
}
.register {
  text-align: center;
  margin-top: 16px;
  font-size: 11px;
}
.bottom {
  margin-top: auto;
  font-size: 10px;
  margin-bottom: 8px;
}

/* ---------- 桌面：认证卡居中限宽 ---------- */
@media (min-width: 1024px) {
  .page {
    max-width: 420px;
    width: 100%;
    margin: 0 auto;
    padding-top: 40px;
    padding-bottom: 60px;
  }

  .headline {
    font-size: 44px;
  }
}
</style>
