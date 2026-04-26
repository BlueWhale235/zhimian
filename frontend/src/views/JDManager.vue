<template>
  <section>
    <PageHeader title="JD 管理" subtitle="粘贴目标岗位描述，系统会尝试提取技能要求。" />
    <div class="two-col">
      <div class="panel">
        <v-text-field v-model="form.title" label="岗位名称" variant="outlined" />
        <v-text-field v-model="form.company" label="公司" variant="outlined" />
        <v-textarea v-model="form.content" label="职位描述" variant="outlined" rows="12" />
        <v-btn color="primary" :loading="loading" @click="create">
          <Plus :size="18" class="mr-2" />保存 JD
        </v-btn>
      </div>
      <div class="jd-list">
        <EmptyState v-if="!jds.length" :icon="BriefcaseBusiness" title="还没有 JD" description="粘贴目标岗位描述后，可用于定向模拟面试。" />
        <JDCard
          v-for="jd in jds"
          v-else
          :key="jd.id"
          :jd="jd"
          :selected="selected?.id === jd.id"
          @select="selected = $event"
          @extract="$emit('extract', $event.id)"
          @delete="askDelete"
        />
      </div>
    </div>

    <v-dialog v-model="detailOpen" max-width="760">
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center">
          {{ selected?.title }}
          <v-spacer />
          <v-btn icon variant="text" aria-label="关闭" @click="selected = null">
            <X :size="18" />
          </v-btn>
        </v-card-title>
        <v-card-subtitle>{{ selected?.company || '未填写公司' }}</v-card-subtitle>
        <v-card-text v-if="selected">
          <h3>提取结果</h3>
          <div class="detail-block">
            <strong>级别：</strong>{{ selected.requirements?.seniority || '未识别' }}
          </div>
          <h4>技能</h4>
          <div class="chip-row">
            <v-chip v-for="item in selected.requirements?.skills || []" :key="item" size="small">{{ item }}</v-chip>
            <span v-if="!(selected.requirements?.skills || []).length" class="muted">暂无</span>
          </div>
          <h4>职责</h4>
          <ul>
            <li v-for="item in selected.requirements?.responsibilities || []" :key="item">{{ item }}</li>
          </ul>
          <h4>关键词</h4>
          <div class="chip-row">
            <v-chip v-for="item in selected.requirements?.keywords || []" :key="item" size="small" variant="tonal">{{ item }}</v-chip>
          </div>
          <v-expansion-panels class="mt-4">
            <v-expansion-panel title="查看 JD 原文">
              <v-expansion-panel-text>
                <p class="jd-content">{{ selected.content }}</p>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
      </v-card>
    </v-dialog>

    <ConfirmDialog
      v-model="confirmOpen"
      title="删除 JD"
      :message="`确定删除「${pendingDelete?.title || ''}」吗？历史面试不会被删除。`"
      confirm-text="删除"
      @confirm="confirmDelete"
    />
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { BriefcaseBusiness, Plus, X } from 'lucide-vue-next'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import JDCard from '../components/JDCard.vue'
import PageHeader from '../components/PageHeader.vue'

defineProps({
  jds: { type: Array, required: true },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['create', 'extract', 'delete', 'toast'])

const form = reactive({ title: '', company: '', content: '' })
const selected = ref(null)
const pendingDelete = ref(null)
const confirmOpen = ref(false)
const detailOpen = computed({
  get: () => Boolean(selected.value),
  set: (value) => {
    if (!value) selected.value = null
  }
})

function create() {
  if (!form.title.trim() || !form.content.trim()) {
    emit('toast', '请填写岗位名称和职位描述。', 'warning')
    return
  }
  emit('create', { ...form })
  Object.assign(form, { title: '', company: '', content: '' })
}

function askDelete(jd) {
  pendingDelete.value = jd
  confirmOpen.value = true
}

function confirmDelete() {
  if (pendingDelete.value) emit('delete', pendingDelete.value.id)
  if (selected.value?.id === pendingDelete.value?.id) selected.value = null
  confirmOpen.value = false
}
</script>
