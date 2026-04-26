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
      <!-- <v-chip color="secondary" variant="tonal" size="small">本地单机版</v-chip> -->
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
import { computed, markRaw, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  BriefcaseBusiness,
  History,
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
  { key: 'interview', label: '模拟面试', icon: markRaw(MessagesSquare), to: '/interview' },
  { key: 'history', label: '历史报告', icon: markRaw(History), to: '/history' },
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
const selectedHistory = ref(null)
const profile = ref(defaultProfile())
const settings = reactive({ base_url: '', api_key: '', model: '', max_rounds: 6, pressure_level: 3, interviewer_prompt: '' })

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
      onDelete: removeResume
    },
    builder: {
      profile: profile.value,
      saveStatus: saveStatus.value,
      'onUpdate:profile': updateProfile,
      onExport: exportProfile
    },
    jds: {
      jds: jds.value,
      onCreate: createJd,
      onExtract: extractJd,
      onDelete: deleteJd
    },
    interview: {
      resumes: resumes.value,
      jds: jds.value,
      activeInterview: activeInterview.value,
      settings,
      onStart: startInterview,
      onAnswer: sendAnswer,
      onFinish: finishActiveInterview,
      onDelete: deleteActiveInterview,
      onSavePrompt: saveInterviewPrompt
    },
    history: {
      interviews: interviews.value,
      selected: selectedHistory.value,
      onRefresh: loadAll,
      onSelect: loadInterview,
      onFinish: finishHistoryInterview,
      onDelete: deleteInterview
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
  }, '面试已开始')
}

async function sendAnswer(content) {
  await run(async () => {
    activeInterview.value = await api.answerInterview(activeInterview.value.session.id, content)
    interviews.value = await api.listInterviews()
  })
}

async function finishActiveInterview() {
  if (!activeInterview.value) return
  await finishInterviewById(activeInterview.value.session.id, true)
}

async function deleteActiveInterview() {
  if (!activeInterview.value) return
  await deleteInterview(activeInterview.value.session.id)
  activeInterview.value = null
}

async function finishHistoryInterview(id) {
  await finishInterviewById(id, false)
}

async function finishInterviewById(id, switchToHistory) {
  await run(async () => {
    const result = await api.finishInterview(id)
    if (activeInterview.value?.session.id === id) activeInterview.value = result
    selectedHistory.value = result
    interviews.value = await api.listInterviews()
    if (switchToHistory) router.push('/history')
  }, 'STAR 报告已生成')
}

async function deleteInterview(id) {
  await run(async () => {
    await api.deleteInterview(id)
    interviews.value = await api.listInterviews()
    if (selectedHistory.value?.session?.id === id) selectedHistory.value = null
    if (activeInterview.value?.session?.id === id) activeInterview.value = null
  }, '面试记录已删除')
}

async function loadInterview(id) {
  selectedHistory.value = await run(() => api.getInterview(id))
}

async function saveSettings(nextSettings) {
  await run(async () => {
    const saved = await api.saveSettings(nextSettings)
    Object.assign(settings, saved)
  }, '设置已保存')
}

async function saveInterviewPrompt(prompt) {
  await saveSettings({ ...settings, interviewer_prompt: prompt })
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
      toast('页面已载入，但暂时无法连接后端。请确认 FastAPI 在 8000 端口运行。', 'warning')
    }
  } finally {
    booting.value = false
  }
})

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
