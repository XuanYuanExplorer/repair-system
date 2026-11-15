<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BField from '@/components/base/BField.vue'
import BButton from '@/components/base/BButton.vue'
import { authApi } from '@/api/auth'
import { errText, isBizError } from '@/api/client'
import { STRENGTH_LABEL, isPhone, passwordStrength } from '@/utils/validate'
import { useCountdown } from '@/composables/useCountdown'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const ui = useUiStore()

const form = reactive({ phone: '', code: '', password: '', confirm: '' })
const errors = reactive<Record<string, string>>({})
const submitting = ref(false)
const sending = ref(false)
const timer = useCountdown(0)
const devCode = ref('')

const strength = computed(() => passwordStrength(form.password))
const info = computed(() => STRENGTH_LABEL[strength.value])
const mismatch = computed(() => !!form.confirm && form.password !== form.confirm)
const canSubmit = computed(() => strength.value !== 'weak' && !mismatch.value && form.code.length >= 4)

async function sendCode() {
  if (!isPhone(form.phone)) {
    errors.phone = '请输入 11 位手机号'
    return
  }
  if (timer.active.value || sending.value) return
  sending.value = true
  errors.phone = ''
  try {
    const res = await authApi.smsCode(form.phone, 'reset')
    timer.start(res.retry_after || 60)
    devCode.value = res.debug_code || ''
    ui.toast(devCode.value ? `验证码已发送（开发环境：${devCode.value}）` : '验证码已发送')
  } catch (e) {
    if (isBizError(e) && e.code === 4003) timer.start(Number((e.data as { retry_after?: number } | null)?.retry_after ?? 60))
    errors.phone = errText(e, '发送失败，请稍后重试')
  } finally {
    sending.value = false
  }
}

async function submit() {
  errors.phone = isPhone(form.phone) ? '' : '请输入 11 位手机号'
  errors.code = form.code.length >= 4 ? '' : '请输入收到的验证码'
  errors.password = strength.value === 'weak' ? '密码需包含字母与数字，至少 6 位' : ''
  errors.confirm = form.password === form.confirm ? '' : '两次输入不一致'
  if (Object.values(errors).some(Boolean)) return

  submitting.value = true
  try {
    await authApi.resetPassword({ phone: form.phone, code: form.code, new_password: form.password })
    ui.toast('密码已重置，请使用新密码登录')
    await router.replace({ name: 'login', query: { account: form.phone } })
  } catch (e) {
    if (isBizError(e) && e.code === 2004) errors.password = '新密码不能与最近 3 次使用过的密码重复'
    else errors.code = errText(e, '重置失败，请检查验证码')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="RESET PASSWORD" title="重置密码" />

      <div class="seg steps" role="tablist">
        <div class="on">01 验证身份</div>
        <div>02 设置新密码</div>
      </div>

      <div class="fields">
        <BField v-model="form.phone" label="手机号" placeholder="注册时预留的手机号" inputmode="tel" :maxlength="11" :error="errors.phone" />
        <BField v-model="form.code" label="验证码" placeholder="6 位验证码" inputmode="numeric" :maxlength="6" :error="errors.code">
          <template #suffix>
            <button type="button" class="send" :disabled="timer.active.value || sending" @click="sendCode">
              {{ timer.active.value ? `重新发送 ${timer.left.value}s` : '获取验证码' }}
            </button>
          </template>
        </BField>
        <BField v-model="form.password" label="新密码" type="password" placeholder="字母 + 数字，至少 6 位" :error="errors.password" autocomplete="new-password" />
      </div>

      <div class="strength">
        <span v-for="i in 3" :key="i" class="bar-seg" :class="{ on: i <= info.level }" />
        <span class="mini">{{ info.en }} {{ info.cn }}</span>
      </div>

      <div class="fields">
        <BField v-model="form.confirm" label="确认密码" type="password" placeholder="再次输入新密码" :error="errors.confirm || (mismatch ? '两次输入不一致，请重新输入' : '')" autocomplete="new-password" />
      </div>

      <p v-if="devCode" class="devcode">开发环境验证码：<b>{{ devCode }}</b></p>

      <p class="rules">· 不能与最近 3 次使用过的密码重复<br />· 建议包含字母、数字与符号组合</p>

      <div class="spacer" />
      <BButton :loading="submitting" :disabled="!canSubmit" @click="submit">确认重置</BButton>
    </div>
  </AppShell>
</template>

<style scoped>
.steps {
  margin-top: 20px;
}
.steps div {
  font-size: 11px;
  color: var(--mute);
}
.steps div.on {
  color: #fff;
}
.fields {
  margin-top: 22px;
}
.send {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: var(--red);
  flex: none;
  white-space: nowrap;
}
.send:disabled {
  color: var(--mute);
  cursor: not-allowed;
}
.strength {
  display: flex;
  gap: 5px;
  align-items: center;
  margin-top: 10px;
}
.bar-seg {
  flex: 1;
  height: 4px;
  background: var(--hair);
}
.bar-seg.on {
  background: var(--ink);
}
.strength .mini {
  margin-left: 4px;
  flex: none;
  text-transform: none;
}
.devcode {
  font-size: 10px;
  color: var(--mute);
  margin-top: 10px;
}
.rules {
  font-size: 9px;
  color: var(--mute);
  line-height: 1.9;
  margin-top: 8px;
  letter-spacing: 0.02em;
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
