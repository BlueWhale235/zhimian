<template>
  <section>
    <PageHeader :title="pageTitle" :subtitle="pageSubtitle">
      <template #actions>
        <v-btn variant="outlined" to="/interview">
          <ArrowLeft :size="18" class="mr-2" />返回列表
        </v-btn>
        <v-btn v-if="activeInterview" color="error" variant="text" :loading="loading" @click="confirmOpen = true">
          <Trash2 :size="18" class="mr-2" />删除
        </v-btn>
      </template>
    </PageHeader>

    <EmptyState
      v-if="!activeInterview"
      :icon="MessagesSquare"
      title="正在读取面试"
      description="如果长时间没有内容，请返回列表重新选择。"
    />

    <div v-else class="interview-detail-grid">
      <div class="panel">
        <div class="section-head mb-3">
          <h2>场次信息</h2>
          <v-chip :color="statusColor(activeInterview.session.status)" size="small" variant="tonal">
            {{ statusLabel(activeInterview.session.status) }}
          </v-chip>
        </div>
        <div class="summary-box">
          <div><strong>简历：</strong>{{ activeInterview.session.resume_name || '未关联简历' }}</div>
          <div><strong>JD：</strong>{{ activeInterview.session.jd_title || 'JD 已删除或未关联' }}</div>
          <div><strong>模式：</strong>{{ activeInterview.session.mode === 'pressure' ? '压力面试' : '普通面试' }}</div>
          <div><strong>回答进度：</strong>{{ userRounds }}/{{ activeInterview.session.max_rounds }}</div>
          <div><strong>创建时间：</strong>{{ activeInterview.session.created_at }}</div>
        </div>

        <v-expansion-panels class="mb-4" variant="accordion">
          <v-expansion-panel title="本场面试 Prompt">
            <v-expansion-panel-text>
              <p class="jd-content">{{ activeInterview.session.interviewer_prompt || '未记录 Prompt。' }}</p>
            </v-expansion-panel-text>
          </v-expansion-panel>
          <v-expansion-panel title="公司背景简介">
            <v-expansion-panel-text>
              <p class="jd-content">{{ activeInterview.session.company_background || '未提供公司背景。' }}</p>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <v-alert v-if="activeInterview.session.status === 'ready_to_finish'" type="info" variant="tonal" class="mb-4">
          已达到最大回答轮数，可以生成 STAR 复盘报告。
        </v-alert>
        <v-alert v-if="activeInterview.session.status === 'finished' && !activeInterview.report" type="warning" variant="tonal" class="mb-4">
          这场面试已结束，但暂时没有报告。可以重新触发生成。
        </v-alert>

        <v-btn
          v-if="activeInterview.session.status !== 'active' && !activeInterview.report"
          block
          color="primary"
          :loading="loading"
          @click="onFinish"
        >
          <Sparkles :size="18" class="mr-2" />生成 STAR 报告
        </v-btn>
      </div>

      <div class="stack">
        <div class="panel">
          <div class="section-head mb-3">
            <h2>面试对话</h2>
            <span class="muted">{{ activeInterview.messages.length }} 条消息</span>
          </div>
          <div ref="chatEl" class="chat detail-chat">
            <ChatMessage v-for="message in activeInterview.messages" :key="message.id" :message="message" />
            <ChatMessage v-if="streamingAssistant" :message="{ role: 'assistant', content: streamingAssistant, created_at: '生成中' }" />
          </div>

          <template v-if="activeInterview.session.status === 'active'">
            <v-textarea
              v-model="answer"
              class="mt-4"
              label="输入回答"
              variant="outlined"
              rows="4"
              :disabled="loading"
              @keydown.ctrl.enter.prevent="submit"
            />
            <div class="form-actions">
              <v-btn color="secondary" :disabled="!answer.trim() || loading" :loading="loading" @click="submit">
                <Send :size="18" class="mr-2" />提交回答
              </v-btn>
            </div>
          </template>
        </div>

        <ReportPanel v-if="activeInterview.report" :report="activeInterview.report" />
      </div>
    </div>

    <ConfirmDialog
      :model-value="confirmOpen"
      title="删除面试"
      message="确定删除当前面试吗？对话记录和复盘报告都会被删除。"
      confirm-text="删除"
      :on-change="value => { confirmOpen = value }"
      :on-confirm="deleteCurrent"
    />
  </section>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowLeft, MessagesSquare, Send, Sparkles, Trash2 } from 'lucide-vue-next'
import ChatMessage from '../components/ChatMessage.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import ReportPanel from '../components/ReportPanel.vue'

const props = defineProps({
  activeInterview: { type: Object, default: null },
  streamingAssistant: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  onAnswer: { type: Function, required: true },
  onFinish: { type: Function, required: true },
  onDelete: { type: Function, required: true }
})
const answer = ref('')
const chatEl = ref(null)
const confirmOpen = ref(false)

const pageTitle = computed(() => props.activeInterview ? `面试 #${props.activeInterview.session.id}` : '面试详情')
const pageSubtitle = computed(() => {
  if (!props.activeInterview) return '继续面试或查看 STAR 复盘报告。'
  return props.activeInterview.session.status === 'finished' ? '这场面试已完成，可以查看报告。' : '这场面试尚未完成，可以继续推进。'
})
const userRounds = computed(() => props.activeInterview?.messages?.filter(item => item.role === 'user').length || 0)

watch(() => props.activeInterview?.messages?.length, scrollChat, { immediate: true })
watch(() => props.streamingAssistant, scrollChat)

function submit() {
  const text = answer.value.trim()
  if (!text) return
  props.onAnswer(text)
  answer.value = ''
}

function deleteCurrent() {
  confirmOpen.value = false
  props.onDelete()
}

function scrollChat() {
  nextTick(() => {
    if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
  })
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
