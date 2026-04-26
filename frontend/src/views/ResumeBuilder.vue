<template>
  <section>
    <PageHeader title="在线简历构建器" subtitle="表单会自动保存，导出后自动进入简历库。">
      <template #actions>
        <v-chip :color="saveColor" variant="tonal">{{ saveLabel }}</v-chip>
        <v-btn color="primary" :loading="loading" @click="exportNow">
          <FileDown :size="18" class="mr-2" />导出 PDF
        </v-btn>
      </template>
    </PageHeader>

    <div class="builder-grid">
      <div class="panel">
        <h2>个人信息</h2>
        <v-row>
          <v-col cols="12" md="6"><v-text-field v-model="local.personal.name" label="姓名" variant="outlined" /></v-col>
          <v-col cols="12" md="6"><v-text-field v-model="local.personal.city" label="城市" variant="outlined" /></v-col>
          <v-col cols="12" md="6"><v-text-field v-model="local.personal.email" label="邮箱" variant="outlined" /></v-col>
          <v-col cols="12" md="6"><v-text-field v-model="local.personal.phone" label="电话" variant="outlined" /></v-col>
        </v-row>
        <v-textarea v-model="local.summary" label="个人总结" variant="outlined" rows="4" />
      </div>
      <ResumeSectionEditor v-model="local.education" title="教育背景" />
      <ResumeSectionEditor v-model="local.internships" title="实习经历" />
      <ResumeSectionEditor v-model="local.projects" title="项目经历" />
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { FileDown } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import ResumeSectionEditor from '../components/ResumeSectionEditor.vue'

const props = defineProps({
  profile: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  saveStatus: { type: String, default: 'saved' }
})

const emit = defineEmits(['update:profile', 'export', 'toast'])

const local = reactive(defaultProfile())
let syncingFromParent = false

watch(() => props.profile, (value) => {
  syncingFromParent = true
  Object.assign(local, defaultProfile(), value || {})
  local.personal = { ...defaultProfile().personal, ...(value?.personal || {}) }
  queueMicrotask(() => {
    syncingFromParent = false
  })
}, { immediate: true, deep: true })

watch(local, () => {
  if (syncingFromParent) return
  emit('update:profile', JSON.parse(JSON.stringify(local)))
}, { deep: true })

const saveLabel = computed(() => ({
  dirty: '未保存',
  saving: '保存中',
  saved: '已保存',
  error: '保存失败'
})[props.saveStatus] || '已保存')

const saveColor = computed(() => ({
  dirty: 'warning',
  saving: 'primary',
  saved: 'secondary',
  error: 'error'
})[props.saveStatus] || 'secondary')

function defaultProfile() {
  return {
    personal: { name: '', city: '', email: '', phone: '' },
    education: [],
    internships: [],
    projects: [],
    summary: ''
  }
}

function exportNow() {
  if (!local.personal.name && !local.summary) {
    emit('toast', '建议先填写姓名或个人总结，仍可继续导出。', 'warning')
  }
  emit('export')
}
</script>
