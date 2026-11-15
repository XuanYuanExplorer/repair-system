<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import BField from '@/components/base/BField.vue'
import BButton from '@/components/base/BButton.vue'
import BIcon from '@/components/base/BIcon.vue'
import { authApi } from '@/api/auth'
import { errText, isBizError } from '@/api/client'
import { STRENGTH_LABEL, isPhone, isStudentNo, passwordStrength } from '@/utils/validate'
import { useUiStore } from '@/stores/ui'

const router = useRouter()
const ui = useUiStore()

const form = reactive({ student_no: '', name: '', phone: '', password: '' })
const errors = reactive<Record<string, string>>({})
const submitting = ref(false)
const checking = ref(false)
const preview = ref<{ room: string; bed_position: string; name_masked: string } | null>(null)
const checkFail = ref('')
const result = ref<{ room: string; bed_no: number; bed_position: string } | null>(null)

const strength = computed(() => passwordStrength(form.password))
const strengthInfo = computed(() => STRENGTH_LABEL[strength.value])
const canSubmit = computed(() => strength.value !== 'weak' && !submitting.value)

async function checkStudent() {
  errors.student_no = ''
  preview.value = null
  checkFail.value = ''
  if (!isStudentNo(form.student_no)) {
    errors.student_no = '请输入 8–12 位学号'
    return
  }
  checking.value = true
  try {
    const res = await authApi.checkStudent(form.student_no)
    if (res.matched) preview.value = { room: res.room, bed_position: res.bed_position, name_masked: res.name_masked }
    else checkFail.value = res.reason || '未查询到在册住宿记录，请联系宿管中心'
  } catch (e) {
    checkFail.value = errText(e, '查询失败，请稍后重试')
  } finally {
    checking.value = false
  }
}

function validate(): boolean {
  errors.student_no = isStudentNo(form.student_no) ? '' : '请输入 8–12 位学号'
  errors.name = form.name.trim().length >= 2 ? '' : '请输入真实姓名'
  errors.phone = isPhone(form.phone) ? '' : '请输入 11 位手机号'
  errors.password = strength.value === 'weak' ? '密码需包含字母与数字，至少 6 位' : ''
  return !Object.values(errors).some(Boolean)
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    const res = await authApi.register({ ...form, name: form.name.trim() })
    result.value = { room: res.room, bed_no: res.bed_no, bed_position: res.bed_position }
    preview.value = null
    ui.toast('认证通过，床位已绑定')
  } catch (e) {
    if (isBizError(e)) {
      if (e.code === 2001 || e.code === 2002) checkFail.value = e.message
      else if (e.code === 2003) errors.student_no = e.message
      else errors.password = e.message
    } else {
      errors.password = errText(e)
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader kicker="REGISTER / 认证" title="注册与身份认证" subtitle="仅限本校在册学生 · 与宿管系统实时核验" />

      <template v-if="!result">
        <div class="fields">
          <BField v-model="form.student_no" label="学号" placeholder="8–12 位学号" :error="errors.student_no" @blur="checkStudent" inputmode="numeric" :maxlength="12" />
          <BField v-model="form.name" label="姓名" placeholder="与学籍一致的姓名" :error="errors.name" :maxlength="20" />
          <BField v-model="form.phone" label="手机号" placeholder="用于接收通知与找回密码" :error="errors.phone" inputmode="tel" :maxlength="11" />
          <BField v-model="form.password" label="设置密码" type="password" placeholder="字母 + 数字，至少 6 位" :error="errors.password" autocomplete="new-password" />
        </div>

        <div class="strength">
          <span v-for="i in 3" :key="i" class="bar-seg" :class="{ on: i <= strengthInfo.level }" />
          <span class="mini" :class="{ red: strength === 'weak' }">{{ strengthInfo.en }} {{ strengthInfo.cn }}</span>
        </div>

        <BButton :loading="submitting" :disabled="!canSubmit" @click="submit">注册并提交认证</BButton>

        <div class="sec"><span class="l"><span class="h-cn">核验结果</span><span class="h-en">VERIFY</span></span></div>

        <div v-if="checking" class="panel verify"><span class="mini">正在核验住宿记录…</span></div>
        <div v-else-if="checkFail" class="panel verify fail">
          <BIcon name="alert" :size="18" />
          <div>
            <b>{{ checkFail }}</b>
            <div class="mini" style="text-transform: none; margin-top: 4px">如需协助请联系宿管中心</div>
            <a class="tel" href="tel:051088186112">0510-8818 6112</a>
          </div>
        </div>
        <div v-else-if="preview" class="panel verify">
          <BIcon name="check" :size="18" class="ok" />
          <div>
            住宿记录匹配成功，已自动绑定<br />
            <b>{{ preview.room }} · {{ preview.bed_position }}</b><br />
            <span class="mute">无需手动选择，信息不可自行修改</span>
          </div>
        </div>
        <p v-else class="mini tip">输入学号后将自动核验住宿记录</p>

        <div class="spacer" />
        <p class="foot">已有账号？<RouterLink to="/login" class="b">返回登录 →</RouterLink></p>
      </template>

      <template v-else>
        <div class="sec"><span class="l"><span class="h-cn">认证完成</span><span class="h-en">VERIFIED</span></span></div>
        <div class="panel done">
          <BIcon name="check" :size="22" class="ok" />
          <div class="done-txt">
            住宿记录匹配成功，已自动绑定<br />
            <b>{{ result.room }} · 床位 {{ result.bed_no }}（{{ result.bed_position }}）</b><br />
            <span class="mute">信息由宿管系统同步，不可自行修改</span>
          </div>
        </div>
        <BButton @click="router.replace({ name: 'login', query: { account: form.student_no } })">进入平台</BButton>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.fields {
  margin-top: 22px;
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
  letter-spacing: 0.1em;
}
.verify {
  padding: 14px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 11px;
  line-height: 1.7;
  border: 1px solid var(--hair);
}
.verify.fail {
  border-left: 3px solid var(--red);
}
.verify.fail b {
  color: var(--red);
}
.ok {
  color: var(--red);
  flex: none;
}
.tel {
  display: inline-block;
  margin-top: 4px;
  font-size: 11px;
  font-weight: 800;
  border-bottom: 1.5px solid var(--ink);
}
.tip {
  text-transform: none;
  letter-spacing: 0.02em;
}
.foot {
  text-align: center;
  font-size: 11px;
  margin-bottom: 6px;
}
.done {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 16px 14px;
  font-size: 11px;
  line-height: 1.8;
  border: var(--line) solid var(--ink);
}
.done-txt b {
  font-size: 12.5px;
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
