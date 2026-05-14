<template>
  <v-app>
    <v-navigation-drawer v-model="drawer" :temporary="isMobile" width="248">
      <div class="brand">
        <div class="brand-mark">职</div>
        <div>
          <div class="brand-title">职面</div>
          <div class="brand-subtitle">智能简历与面试</div>
        </div>
      </div>
      <v-list nav density="compact">
        <v-list-item
          v-for="item in nav"
          :key="item.key"
          :active="activeNavKey === item.key"
          color="primary"
          rounded="lg"
          :to="item.to"
        >
          <template #prepend><component :is="item.icon" :size="18" /></template>
          <v-list-item-title>{{ item.label }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar flat border color="white">
      <v-btn icon variant="text" aria-label="打开导航" @click="drawer = !drawer">
        <Menu :size="20" />
      </v-btn>
      <v-app-bar-title>{{ currentTitle }}</v-app-bar-title>
      <v-chip color="secondary" variant="tonal" size="small">本地单机版</v-chip>
    </v-app-bar>

    <v-main>
      <div class="page">
        <v-alert v-if="notice" class="mb-4" :type="noticeType" closable @click:close="notice = ''">
          {{ notice }}
        </v-alert>

        <router-view v-bind="routeProps" />
      </div>
    </v-main>

    <LoadingOverlay :model-value="booting" />
  </v-app>
</template>

<script setup>
import { computed, markRaw, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BriefcaseBusiness,
  Menu,
  MessagesSquare,
  PenLine,
  Settings,
  Upload
} from 'lucide-vue-next'
import { api } from './api'
import LoadingOverlay from './components/LoadingOverlay.vue'

const nav = [
  { key: 'resumes', label: '简历库', icon: markRaw(Upload), to: '/resumes' },
  { key: 'builder', label: '在线构建', icon: markRaw(PenLine), to: '/builder' },
  { key: 'jds', label: 'JD 管理', icon: markRaw(BriefcaseBusiness), to: '/jds' },
  { key: 'interview', label: '面试与报告', icon: markRaw(MessagesSquare), to: '/interview' },
  { key: 'settings', label: '系统设置', icon: markRaw(Settings), to: '/settings' }
]

const route = useRoute()
const router = useRouter()
const drawer = ref(true)
const width = ref(window.innerWidth)
const loading = ref(false)
const booting = ref(true)
const checkingHealth = ref(false)
const notice = ref('')
const noticeType = ref('success')
const healthOk = ref(false)
const saveStatus = ref('saved')
const saveTimer = ref(null)
const resumes = ref([])
const jds = ref([])
const interviews = ref([])
const activeInterview = ref(null)
const streamingAssistant = ref('')
const profile = ref(defaultProfile())
const settings = reactive({
  base_url: '',
  api_key: '',
  model: '',
  jd_model: '',
  url_extract_model: '',
  resume_extract_model: '',
  interview_model: '',
  report_model: '',
  max_rounds: 6,
  pressure_level: 3,
  normal_interviewer_prompt: '',
  pressure_interviewer_prompt: ''
})

const isMobile = computed(() => width.value < 900)
const activeNavKey = computed(() => route.meta.navKey || 'resumes')
const currentTitle = computed(() => route.meta.title || '职面')
const routeProps = computed(() => {
  const common = {
    loading: loading.value,
    onToast: toast
  }
  const map = {
    resumes: {
      resumes: resumes.value,
      onUpload: uploadResume,
      onExtractText: extractResumeText,
      onDelete: removeResume
    },
    builder: {
      profile: profile.value,
      saveStatus: saveStatus.value,
      onChange: updateProfile,
      onExport: exportProfile
    },
    jds: {
      jds: jds.value,
      extractUrl: extractJdFromUrl,
      onCreate: createJd,
      onUpdate: updateJd,
      onExtract: extractJd,
      onDelete: deleteJd
    },
    interviewCenter: {
      resumes: resumes.value,
      jds: jds.value,
      interviews: interviews.value,
      settings,
      onStart: startInterview,
      onDelete: deleteInterview,
      onSavePrompt: saveInterviewPrompt,
      onRefresh: loadAll
    },
    interviewDetail: {
      activeInterview: activeInterview.value,
      streamingAssistant: streamingAssistant.value,
      onAnswer: sendAnswer,
      onFinish: finishActiveInterview,
      onDelete: deleteActiveInterview
    },
    settings: {
      settings,
      healthOk: healthOk.value,
      checking: checkingHealth.value,
      onSave: saveSettings,
      onCheckHealth: checkHealth
    }
  }
  return { ...common, ...(map[route.meta.propsKey] || {}) }
})

function defaultProfile() {
  return {
    personal: { name: '', city: '', email: '', phone: '' },
    education: [],
    internships: [],
    projects: [],
    summary: ''
  }
}

function toast(message, type = 'success') {
  notice.value = message
  noticeType.value = type
}

async function run(task, success) {
  loading.value = true
  try {
    const result = await task()
    if (success) toast(success)
    return result
  } catch (error) {
    toast(error.message || '操作失败', 'error')
    return null
  } finally {
    loading.value = false
  }
}

async function loadAll({ quiet = false } = {}) {
  const tasks = await Promise.allSettled([
    api.listResumes(),
    api.listJds(),
    api.listInterviews(),
    api.getSettings(),
    api.getProfile()
  ])
  const [resumeData, jdData, interviewData, settingsData, profileData] = tasks
  if (resumeData.status === 'fulfilled') resumes.value = resumeData.value
  if (jdData.status === 'fulfilled') jds.value = jdData.value
  if (interviewData.status === 'fulfilled') interviews.value = interviewData.value
  if (settingsData.status === 'fulfilled') Object.assign(settings, settingsData.value)
  if (profileData.status === 'fulfilled') {
    profile.value = { ...defaultProfile(), ...(profileData.value.data || {}) }
    profile.value.personal = { ...defaultProfile().personal, ...(profileData.value.data?.personal || {}) }
  }
  const failed = tasks.find(item => item.status === 'rejected')
  if (failed && !quiet) {
    toast(failed.reason?.message || '初始化数据失败，请确认后端服务。', 'warning')
  }
}

async function checkHealth() {
  checkingHealth.value = true
  try {
    const response = await api.health()
    healthOk.value = response.status === 'ok'
  } catch {
    healthOk.value = false
  } finally {
    checkingHealth.value = false
  }
}

async function uploadResume(file) {
  await run(async () => {
    await api.uploadResume(file)
    resumes.value = await api.listResumes()
  }, '简历已上传')
}

async function removeResume(id) {
  await run(async () => {
    await api.deleteResume(id)
    resumes.value = await api.listResumes()
  }, '简历已删除')
}

async function extractResumeText(id) {
  await run(async () => {
    const updated = await api.extractResumeText(id)
    resumes.value = resumes.value.map(item => item.id === updated.id ? updated : item)
  }, '简历文本已提取')
}

function updateProfile(nextProfile) {
  profile.value = nextProfile
  saveStatus.value = 'dirty'
  clearTimeout(saveTimer.value)
  saveTimer.value = setTimeout(saveProfileDraft, 700)
}

async function saveProfileDraft() {
  saveStatus.value = 'saving'
  try {
    await api.saveProfile(profile.value)
    saveStatus.value = 'saved'
  } catch {
    saveStatus.value = 'error'
  }
}

async function exportProfile() {
  await run(async () => {
    await saveProfileDraft()
    await api.exportProfile()
    resumes.value = await api.listResumes()
    router.push('/resumes')
  }, '在线简历已导出')
}

async function createJd(payload) {
  await run(async () => {
    await api.createJd(payload)
    jds.value = await api.listJds()
  }, 'JD 已保存')
}

async function extractJdFromUrl(url) {
  return run(() => api.extractJdFromUrl(url))
}

async function updateJd(payload) {
  await run(async () => {
    await api.updateJd(payload.id, payload)
    jds.value = await api.listJds()
  }, 'JD 已更新')
}

async function extractJd(id) {
  await run(async () => {
    await api.extractJd(id)
    jds.value = await api.listJds()
  }, 'JD 要求已更新')
}

async function deleteJd(id) {
  await run(async () => {
    await api.deleteJd(id)
    jds.value = await api.listJds()
    interviews.value = await api.listInterviews()
  }, 'JD 已删除')
}

async function startInterview(payload) {
  await run(async () => {
    activeInterview.value = await api.createInterview(payload)
    interviews.value = await api.listInterviews()
    router.push(`/interview/${activeInterview.value.session.id}`)
  }, '面试已开始')
}

async function sendAnswer(content) {
  if (!activeInterview.value) return
  await run(async () => {
    const current = activeInterview.value
    activeInterview.value = {
      ...current,
      messages: [
        ...current.messages,
        { id: `user-${Date.now()}`, role: 'user', content, created_at: '刚刚' }
      ]
    }
    streamingAssistant.value = ''
    activeInterview.value = await api.answerInterviewStream(current.session.id, content, delta => {
      streamingAssistant.value += delta
    })
    streamingAssistant.value = ''
    interviews.value = await api.listInterviews()
  })
}

async function finishActiveInterview() {
  if (!activeInterview.value) return
  await finishInterviewById(activeInterview.value.session.id)
}

async function deleteActiveInterview() {
  if (!activeInterview.value) return
  await deleteInterview(activeInterview.value.session.id)
}

async function finishInterviewById(id) {
  await run(async () => {
    const result = await api.finishInterview(id)
    activeInterview.value = result
    interviews.value = await api.listInterviews()
    router.push(`/interview/${id}`)
  }, 'STAR 报告已生成')
}

async function deleteInterview(id) {
  await run(async () => {
    await api.deleteInterview(id)
    interviews.value = await api.listInterviews()
    if (activeInterview.value?.session?.id === id) activeInterview.value = null
    if (route.name === 'interview-detail' && String(route.params.id) === String(id)) router.push('/interview')
  }, '面试记录已删除')
}

async function loadActiveInterview(id) {
  const result = await run(() => api.getInterview(id))
  if (result) activeInterview.value = result
}

async function saveSettings(nextSettings) {
  await run(async () => {
    const saved = await api.saveSettings(nextSettings)
    Object.assign(settings, saved)
  }, '设置已保存')
}

async function saveInterviewPrompt({ mode, prompt }) {
  const key = mode === 'pressure' ? 'pressure_interviewer_prompt' : 'normal_interviewer_prompt'
  await saveSettings({ ...settings, [key]: prompt })
}

function onResize() {
  width.value = window.innerWidth
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  try {
    await Promise.race([
      Promise.allSettled([loadAll({ quiet: true }), checkHealth()]),
      new Promise(resolve => window.setTimeout(resolve, 9000))
    ])
    if (!healthOk.value) {
      toast('页面已加载，但暂时无法连接后端。请确认 FastAPI 在 8000 端口运行。', 'warning')
    }
  } finally {
    booting.value = false
  }
})

watch(() => [route.name, route.params.id], ([name, id]) => {
  if (name === 'interview-detail' && id) {
    loadActiveInterview(id)
  } else if (name === 'interview') {
    activeInterview.value = null
    streamingAssistant.value = ''
  }
}, { immediate: true })

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  clearTimeout(saveTimer.value)
})
</script>

<style scoped>
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  color: white;
  background: #2563eb;
  font-weight: 800;
}

.brand-title {
  font-weight: 800;
}

.brand-subtitle {
  color: #64748b;
  font-size: 12px;
}
</style>
