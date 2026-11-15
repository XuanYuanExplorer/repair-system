<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import SearchInput from '@/components/form/SearchInput.vue'
import BIcon from '@/components/base/BIcon.vue'
import BTag from '@/components/base/BTag.vue'
import { helpApi } from '@/api/help'
import { useAsyncData } from '@/composables/useAsyncData'
import { useDebouncedRef } from '@/composables/useDebounce'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const ui = useUiStore()
const auth = useAuthStore()

const keyword = ref('')
const debounced = useDebouncedRef(keyword, 300)
const { data, loading, refresh } = useAsyncData('help:faqs', () => helpApi.faqs(debounced.value || undefined))
const hotlines = useAsyncData('help:hotlines', helpApi.hotlines)

const openId = ref<number | null>(1)

const faqs = computed(() => data.value || [])
const empty = computed(() => !loading.value && !faqs.value.length)

function toggle(id: number) {
  openId.value = openId.value === id ? null : id
}

function search(tag: string) {
  keyword.value = tag
  void refresh()
}

function call(phone: string) {
  window.location.href = `tel:${phone.replace(/[^\d+]/g, '')}`
}
</script>

<template>
  <AppShell>
    <div class="page">
      <PageHeader
        kicker="HELP CENTER"
        title="帮助中心"
        :back="auth.isLogged"
        subtitle="常见问题、自助排查与人工服务电话"
        @back="router.back()"
      />

      <SearchInput v-model="keyword" placeholder="搜索问题，如「跳闸」「发票」" @submit="refresh()" />

      <div class="sec"><span class="l"><span class="h-cn">常见问题</span><span class="h-en">FAQ</span></span><span class="all">{{ faqs.length }} 条</span></div>

      <div v-if="empty" class="nofaq">
        <BIcon name="search" :size="20" />
        <p>没有找到相关问题，试试「报修」「电费」</p>
        <div class="chips quick">
          <button v-for="t in ['报修', '电费', '发票', '跳闸']" :key="t" type="button" class="chip" @click="search(t)">{{ t }}</button>
        </div>
      </div>

      <div v-for="f in faqs" :key="f.id" class="faq">
        <button type="button" class="fhead" :aria-expanded="openId === f.id" @click="toggle(f.id)">
          <span class="fq">
            <span class="fidx num-lg">{{ String(f.index).padStart(2, '0') }}</span>
            {{ f.question }}
            <BTag v-if="f.is_self_help" tone="red" sm text="自助" />
          </span>
          <BIcon :name="openId === f.id ? 'minus' : 'plus'" :size="13" class="fmark" />
        </button>
        <p v-if="openId === f.id" class="fans">{{ f.answer }}</p>
      </div>

      <div class="sec"><span class="l"><span class="h-cn">服务电话</span><span class="h-en">HOTLINE</span></span></div>
      <button v-for="h in hotlines.data.value || []" :key="h.phone" type="button" class="hot" @click="call(h.phone)">
        <span class="hinfo">
          <b>{{ h.name }}</b>
          <span class="mini htime">{{ h.time }}</span>
        </span>
        <span class="hnum num-lg">{{ h.phone }}</span>
        <BIcon name="phone" :size="14" />
      </button>

      <div class="spacer" />
      <button type="button" class="btn red" @click="call(hotlines.data.value?.[0]?.phone || '051088186112')">
        <BIcon name="alert" :size="15" />紧急情况 · 一键拨号
      </button>
      <p class="hint">非紧急事项建议先提交报修工单，便于留痕与跟踪</p>
    </div>
  </AppShell>
</template>

<style scoped>
.faq {
  border-bottom: 1px solid var(--hair);
}
.fhead {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 12px 0;
  text-align: left;
}
.fq {
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1.5;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.fidx {
  font-size: 10px;
  color: var(--mute);
}
.fmark {
  color: var(--ghost);
  flex: none;
  margin-top: 2px;
}
.fans {
  font-size: 11px;
  color: #5a5a58;
  line-height: 1.8;
  padding: 0 0 12px 20px;
}
.nofaq {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 0;
  color: var(--mute);
  font-size: 11px;
  text-align: center;
}
.quick {
  justify-content: center;
}
.hot {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 0;
  border-bottom: 1px solid var(--hair);
  text-align: left;
}
.hinfo {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 12.5px;
}
.htime {
  text-transform: none;
  letter-spacing: 0.02em;
}
.hnum {
  font-size: 13px;
  color: var(--ink);
}
.hint {
  font-size: 9px;
  color: var(--mute);
  text-align: center;
  margin-top: 10px;
  line-height: 1.7;
}
.btn.red {
  margin-top: 8px;
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
