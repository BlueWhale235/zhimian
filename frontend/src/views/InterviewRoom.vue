<template>
  <section>
    <PageHeader title="模拟面试" subtitle="选择简历与 JD，使用文字回答完成第一版面试闭环。" />
    <div class="two-col interview-layout">
      <div class="panel">
        <v-select v-model="form.resume_id" :disabled="inProgress" :items="resumes" item-title="original_name" item-value="id" label="简历" variant="outlined" clearable />
        <v-select v-model="form.jd_id" :disabled="inProgress" :items="jds" item-title="title" item-value="id" label="目标 JD" variant="outlined" clearable />
        <v-select v-model="form.mode" :disabled="inProgress" :items="modeItems" label="模式" variant="outlined" />
        <v-slider v-model="form.max_rounds" :disabled="inProgress" label="最大轮数" min="1" max="20" step="1" thumb-label />
        <v-slider v-model="form.pressure_level" :disabled="inProgress || form.mode !== 'pressure'" label="压力强度" min="1" max="5" step="1" thumb-label />
        <v-textarea
          v-model="form.interviewer_prompt"
          :disabled="inProgress"
          label="面试官 Prompt"
          variant="outlined"
          rows="6"
          auto-grow
        />
        <v-btn class="mb-3" variant="outlined" block :disabled="inProgress || loading" @click="$emit('save-prompt', form.interviewer_prompt)">
          <Save :size="18" class="mr-2" />保存为默认 Prompt
        </v-btn>

        <div class="summary-box">
          <div><strong>简历：</strong>{{ selectedResume?.original_name || '未选择' }}</div>
          <div><strong>JD：</strong>{{ selectedJd?.title || '未选择' }}</div>
          <div><strong>模式：</strong>{{ form.mode === 'pressure' ? '压力面试' : '普通面试' }}</div>
          <div><strong>轮数：</strong>{{ userRounds }}/{{ form.max_rounds }}</div>
        </div>

        <v-btn v-if="!activeInterview" block color="primary" :loading="loading" @click="$emit('start', { ...form })">
          <MessagesSquare :size="18" class="mr-2" />开始面试
        </v-btn>
        <v-btn v-else block class="mt-2" variant="outlined" :disabled="activeInterview.session.status === 'finished'" :loading="loading" @click="$emit('finish')">
          <CheckCircle2 :size="18" class="mr-2" />{{ finishLabel }}
        </v-btn>
        <v-btn v-if="activeInterview" block class="mt-2" color="error" variant="text" :loading="loading" @click="confirmOpen = true">
          <Trash2 :size="18" class="mr-2" />删除本场面试
        </v-btn>
      </div>

      <div class="panel">
        <EmptyState v-if="!activeInterview" :icon="MessagesSquare" title="尚未开始面试" description="配置面试参数后，AI 面试官会生成第一道问题。" />
        <template v-else>
          <div ref="chatEl" class="chat">
            <ChatMessage v-for="message in activeInterview.messages" :key="message.id" :message="message" />
          </div>
          <v-alert v-if="activeInterview.session.status === 'ready_to_finish'" class="mt-4" type="info" variant="tonal">
            已达到最大轮数，可以结束并生成 STAR 报告。
          </v-alert>
          <v-alert v-if="activeInterview.session.status === 'finished'" class="mt-4" type="success" variant="tonal">
            面试已结束，可在历史报告中查看复盘。
          </v-alert>
          <v-textarea
            v-if="activeInterview.session.status === 'active'"
            v-model="answer"
            class="mt-4"
            label="输入你的回答"
            variant="outlined"
            rows="4"
            :disabled="loading"
            @keydown.ctrl.enter.prevent="submit"
          />
          <v-btn
            v-if="activeInterview.session.status === 'active'"
            color="secondary"
            :disabled="!answer.trim() || loading"
            :loading="loading"
            @click="submit"
          >
            <Send :size="18" class="mr-2" />提交回答
          </v-btn>
        </template>
      </div>
    </div>

    <ConfirmDialog
      v-model="confirmOpen"
      title="删除面试"
      message="确定删除当前面试吗？对话记录和复盘报告都会被删除。"
      confirm-text="删除"
      @confirm="deleteCurrent"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { CheckCircle2, MessagesSquare, Save, Send, Trash2 } from 'lucide-vue-next'
import ChatMessage from '../components/ChatMessage.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'

const props = defineProps({
  resumes: { type: Array, required: true },
  jds: { type: Array, required: true },
  activeInterview: { type: Object, default: null },
  settings: { type: Object, required: true },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['start', 'answer', 'finish', 'delete', 'save-prompt'])

const answer = ref('')
const chatEl = ref(null)
const confirmOpen = ref(false)
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
  if (!props.activeInterview) {
    form.interviewer_prompt = value.interviewer_prompt || ''
  }
}, { immediate: true, deep: true })

watch(() => props.activeInterview?.session?.interviewer_prompt, (value) => {
  if (value) form.interviewer_prompt = value
})

watch(() => props.activeInterview?.messages?.length, () => {
  nextTick(() => {
    if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
  })
})

const inProgress = computed(() => props.activeInterview && props.activeInterview.session.status !== 'finished')
const selectedResume = computed(() => props.resumes.find(item => item.id === form.resume_id))
const selectedJd = computed(() => props.jds.find(item => item.id === form.jd_id))
const userRounds = computed(() => props.activeInterview?.messages?.filter(item => item.role === 'user').length || 0)
const finishLabel = computed(() => props.activeInterview?.session.status === 'ready_to_finish' ? '生成 STAR 报告' : '结束并生成报告')

function submit() {
  const text = answer.value.trim()
  if (!text) return
  emit('answer', text)
  answer.value = ''
}

function deleteCurrent() {
  confirmOpen.value = false
  emit('delete')
}
</script>
