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
      <ResumeSectionEditor title="教育背景" :items="local.education" :on-change="value => setSection('education', value)" />
      <ResumeSectionEditor title="实习经历" :items="local.internships" :on-change="value => setSection('internships', value)" />
      <ResumeSectionEditor title="项目经历" :items="local.projects" :on-change="value => setSection('projects', value)" />
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
  saveStatus: { type: String, default: 'saved' },
  onChange: { type: Function, required: true },
  onExport: { type: Function, required: true },
  onToast: { type: Function, required: true }
})

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
  props.onChange(JSON.parse(JSON.stringify(local)))
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

function setSection(key, value) {
  local[key] = value
}

function exportNow() {
  if (!local.personal.name && !local.summary) {
    props.onToast('建议先填写姓名或个人总结，仍可继续导出。', 'warning')
  }
  props.onExport()
}
</script>
