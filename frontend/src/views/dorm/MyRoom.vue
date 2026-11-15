<script setup lang="ts">
import { useRouter } from 'vue-router'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import FacilityRow from '@/components/data/FacilityRow.vue'
import BButton from '@/components/base/BButton.vue'
import BIcon from '@/components/base/BIcon.vue'
import SkeletonList from '@/components/feedback/SkeletonList.vue'
import ErrorRetry from '@/components/feedback/ErrorRetry.vue'
import { dormApi } from '@/api/dorm'
import { useAsyncData } from '@/composables/useAsyncData'

const router = useRouter()
const { data, loading, error, refresh } = useAsyncData('dorm:my-room', dormApi.myRoom)

function repairFor(category: string, spot: string) {
  router.push({
    path: '/repair/submit',
    query: { room_id: String(data.value?.id || ''), category, spot, desc: `${spot}故障（由设施清单发起）` },
  })
}

const quick = [
  { label: '寝室成员', en: 'MEMBERS', icon: 'user', to: '/dorm/members' },
  { label: '值日排班', en: 'DUTY', icon: 'cal', to: '/dorm/duty' },
  { label: '公告公约', en: 'NOTICE', icon: 'doc', to: '/dorm/notice' },
]
</script>

<template>
  <AppShell tab="profile">
    <div class="page">
      <PageHeader kicker="MY ROOM" :title="data?.title || '我的寝室'" :subtitle="data?.subtitle" />

      <SkeletonList v-if="loading && !data" :rows="3" variant="detail" />
      <ErrorRetry v-else-if="error && !data" :message="error" @retry="refresh()" />

      <template v-else-if="data">
        <div class="statgrid quad">
          <div><span class="mini">床位</span><span class="num-lg sv">{{ data.capacity }}</span></div>
          <div><span class="mini">入住</span><span class="num-lg sv">{{ data.occupied }}</span></div>
          <div><span class="mini">寝室长</span><span class="txtv">{{ data.leader_name || '—' }}</span></div>
          <div><span class="mini">我的床位</span><span class="txtv red">{{ data.my_bed.bed_no }} 号 · {{ data.my_bed.position_label }}</span></div>
        </div>

        <div class="sec">
          <span class="l"><span class="h-cn">公共设施清单</span><span class="h-en">FACILITY</span></span>
          <span class="all">{{ data.facilities.length }} 项</span>
        </div>
        <div class="facilities">
          <FacilityRow
            v-for="f in data.facilities"
            :key="f.id"
            :facility="f"
            @repair="repairFor(f.category, f.name)"
          />
        </div>

        <div class="sec"><span class="l"><span class="h-cn">快捷操作</span><span class="h-en">QUICK</span></span></div>
        <div class="quick">
          <button v-for="q in quick" :key="q.to" type="button" class="qcell" @click="router.push(q.to)">
            <BIcon :name="q.icon" :size="18" />
            <span class="qlabel">{{ q.label }}</span>
            <span class="qen">{{ q.en }}</span>
          </button>
        </div>

        <div class="spacer" />
        <BButton @click="repairFor('public', '公共区域')">
          <BIcon name="tool" :size="15" />设施报修 · 自动带入房间位置
        </BButton>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.quad > div {
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sv {
  font-size: 20px;
}
.txtv {
  font-size: 12px;
  font-weight: 800;
  margin-top: 2px;
}
.quick {
  display: flex;
  border: 1px solid var(--hair);
}
.qcell {
  flex: 1;
  padding: 14px 6px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  border-right: 1px solid var(--hair);
}
.qcell:last-child {
  border-right: none;
}
.qcell:active {
  opacity: 0.6;
}
.qlabel {
  font-size: 11px;
  font-weight: 700;
}
.qen {
  font-size: 7.5px;
  letter-spacing: 0.2em;
  color: var(--mute);
  font-weight: 700;
}

/* ---------- 桌面：设施两列、快捷区域放大 ---------- */
@media (min-width: 1024px) {
  .statgrid.quad {
    margin-top: 20px;
  }

  .statgrid.quad .sv {
    font-size: 30px;
  }

  .facilities {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 40px;
  }

  .facilities :deep(.row) {
    padding: 15px 0;
    border-bottom: 1px solid var(--hair);
  }

  .facilities :deep(.name) {
    font-size: 14px;
  }

  .quick {
    margin-top: 6px;
  }

  .qcell {
    padding: 22px 8px 18px;
  }

  .qlabel {
    font-size: 13px;
  }
}
</style>
