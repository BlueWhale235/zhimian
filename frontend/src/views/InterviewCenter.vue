<template>
  <section>
    <PageHeader title="面试与报告" subtitle="创建新的模拟面试，或从列表继续未完成场次、查看已完成报告。">
      <template #actions>
        <v-btn variant="outlined" :loading="loading" @click="props.onRefresh">
          <RefreshCw :size="18" class="mr-2" />刷新
        </v-btn>
        <v-btn color="primary" @click="createOpen = true">
          <Plus :size="18" class="mr-2" />新建面试
        </v-btn>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="section-head mb-3">
        <h2>面试列表</h2>
        <v-chip size="small" variant="tonal">{{ interviews.length }} 场</v-chip>
      </div>
      <EmptyState
        v-if="!interviews.length"
        :icon="FileSearch"
        title="还没有面试记录"
        description="点击右上角“新建面试”，创建一场面试后可以在这里继续或查看报告。"
      />
      <div v-else class="session-list">
        <div
          v-for="session in interviews"
          :key="session.id"
          class="session-row"
          role="button"
          tabindex="0"
          @click="openSession(session)"
          @keydown.enter.prevent="openSession(session)"
        >
          <div class="session-main">
            <div class="session-title">
              <span>#{{ session.id }} {{ session.jd_title || 'JD 已删除或未关联' }}</span>
              <v-chip :color="statusColor(session.status)" size="small" variant="tonal">{{ statusLabel(session.status) }}</v-chip>
            </div>
            <div class="session-meta">
              <span>{{ session.resume_name || '未关联简历' }}</span>
              <span>{{ session.mode === 'pressure' ? '压力面试' : '普通面试' }}</span>
              <span>{{ session.created_at }}</span>
            </div>
          </div>
          <div class="session-actions">
            <v-btn size="small" color="primary" variant="outlined" @click.stop="openSession(session)">
              {{ session.status === 'finished' ? '查看报告' : '继续面试' }}
            </v-btn>
            <v-btn icon size="small" variant="text" color="error" aria-label="删除面试" @click.stop="askDelete(session)">
              <Trash2 :size="17" />
            </v-btn>
          </div>
        </div>
      </div>
    </div>

    <v-dialog v-model="createOpen" max-width="760" scrollable>
      <v-card rounded="lg">
        <v-card-title class="detail-title">
          <div>
            新建面试
            <div class="text-caption text-medium-emphasis">配置简历、JD、面试模式和本场 Prompt。</div>
          </div>
          <v-btn icon variant="text" aria-label="关闭" @click="createOpen = false">
            <X :size="18" />
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-select v-model="form.resume_id" :items="resumes" item-title="original_name" item-value="id" label="简历" variant="outlined" clearable />
          <v-select v-model="form.jd_id" :items="jds" item-title="title" item-value="id" label="目标 JD" variant="outlined" clearable />
          <v-alert v-if="selectedResume && !selectedResume.has_parsed_text" class="mb-4" type="warning" variant="tonal">
            这份简历还没有有效提取文本，面试官可能只能看到文件名，围绕简历追问的质量会下降。可以先到简历预览里使用 AI 提取。
          </v-alert>
          <v-alert v-if="!selectedJd" class="mb-4" type="info" variant="tonal">
            当前未选择 JD，面试会进入通用求职闲聊模式，不会针对具体岗位要求追问。
          </v-alert>
          <v-select v-model="form.mode" :items="modeItems" label="模式" variant="outlined" />
          <v-slider v-model="form.max_rounds" label="最大回答轮数" min="1" max="20" step="1" thumb-label />
          <v-slider v-model="form.pressure_level" :disabled="form.mode !== 'pressure'" label="压力强度" min="1" max="5" step="1" thumb-label />

          <v-expansion-panels class="mb-4" variant="accordion">
            <v-expansion-panel title="公司背景简介">
              <v-expansion-panel-text>
                <p class="muted mb-3">这里读取 JD 管理中保存的公司背景，会作为面试上下文的一部分。</p>
                <p class="jd-content">{{ selectedJd?.company_background || '未提供公司背景。' }}</p>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <v-textarea
            v-model="form.interviewer_prompt"
            :label="form.mode === 'pressure' ? '压力面试 Prompt' : '普通面试 Prompt'"
            variant="outlined"
            rows="6"
            auto-grow
            counter="5000"
          />

          <div class="summary-box">
            <div><strong>简历：</strong>{{ selectedResume?.original_name || '未选择' }}</div>
            <div><strong>JD：</strong>{{ selectedJd?.title || '未选择' }}</div>
            <div><strong>模式：</strong>{{ form.mode === 'pressure' ? '压力面试' : '普通面试' }}</div>
            <div><strong>回答轮数：</strong>{{ form.max_rounds }}</div>
          </div>
        </v-card-text>
        <v-card-actions class="px-6 pb-5">
          <v-btn variant="outlined" :disabled="loading" @click="props.onSavePrompt({ mode: form.mode, prompt: form.interviewer_prompt })">
            <Save :size="18" class="mr-2" />保存为默认 Prompt
          </v-btn>
          <v-spacer />
          <v-btn variant="text" @click="createOpen = false">取消</v-btn>
          <v-btn color="primary" :loading="loading" @click="startNewInterview">
            <MessagesSquare :size="18" class="mr-2" />开始面试
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog
      :model-value="confirmOpen"
      title="删除面试记录"
      :message="`确定删除 #${pendingDelete?.id || ''} 这场面试吗？对话记录和复盘报告都会被删除。`"
      confirm-text="删除"
      :on-change="value => { confirmOpen = value }"
      :on-confirm="confirmDelete"
    />
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FileSearch, MessagesSquare, Plus, RefreshCw, Save, Trash2, X } from 'lucide-vue-next'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'

const props = defineProps({
  resumes: { type: Array, required: true },
  jds: { type: Array, required: true },
  interviews: { type: Array, required: true },
  settings: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  onStart: { type: Function, required: true },
  onDelete: { type: Function, required: true },
  onSavePrompt: { type: Function, required: true },
  onRefresh: { type: Function, required: true }
})
const router = useRouter()
const createOpen = ref(false)
const confirmOpen = ref(false)
const pendingDelete = ref(null)

const form = reactive({
  resume_id: null,
  jd_id: null,
  mode: 'normal',
  max_rounds: 6,
  pressure_level: 3,
  interviewer_prompt: ''
})

const modeItems = [
  { title: '普通面试', value: 'normal' },
  { title: '压力面试', value: 'pressure' }
]

watch(() => props.settings, (value) => {
  form.max_rounds = Number(value.max_rounds || 6)
  form.pressure_level = Number(value.pressure_level || 3)
  form.interviewer_prompt = form.mode === 'pressure' ? (value.pressure_interviewer_prompt || '') : (value.normal_interviewer_prompt || '')
}, { immediate: true, deep: true })

watch(() => form.mode, (mode) => {
  form.interviewer_prompt = mode === 'pressure' ? (props.settings.pressure_interviewer_prompt || '') : (props.settings.normal_interviewer_prompt || '')
})

const selectedResume = computed(() => props.resumes.find(item => item.id === form.resume_id))
const selectedJd = computed(() => props.jds.find(item => item.id === form.jd_id))

function openSession(session) {
  router.push(`/interview/${session.id}`)
}

function startNewInterview() {
  createOpen.value = false
  props.onStart({ ...form })
}

function askDelete(session) {
  pendingDelete.value = session
  confirmOpen.value = true
}

function confirmDelete() {
  if (pendingDelete.value) props.onDelete(pendingDelete.value.id)
  confirmOpen.value = false
}

function statusLabel(status) {
  return {
    active: '进行中',
    ready_to_finish: '待生成报告',
    finished: '已完成'
  }[status] || status
}

function statusColor(status) {
  return {
    active: 'primary',
    ready_to_finish: 'warning',
    finished: 'success'
  }[status] || 'default'
}
</script>
