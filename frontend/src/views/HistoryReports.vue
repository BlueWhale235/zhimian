<template>
  <section>
    <PageHeader title="历史报告" subtitle="回看往期 transcript 与 STAR 复盘。">
      <template #actions>
        <v-btn variant="outlined" @click="onRefresh">
          <RefreshCw :size="18" class="mr-2" />刷新
        </v-btn>
      </template>
    </PageHeader>

    <div class="history-layout">
      <div class="history-list panel">
        <EmptyState v-if="!interviews.length" :icon="History" title="暂无历史场次" description="完成一次模拟面试后，这里会出现完整记录。" />
        <v-list v-else density="compact">
          <v-list-item
            v-for="session in interviews"
            :key="session.id"
            :active="selected?.session?.id === session.id"
            rounded="lg"
            @click="onSelect(session.id)"
          >
            <v-list-item-title>#{{ session.id }} · {{ session.jd_title || 'JD 已删除或未关联' }}</v-list-item-title>
            <v-list-item-subtitle>{{ statusLabel(session.status) }} · {{ session.created_at }}</v-list-item-subtitle>
            <template #append>
              <v-btn icon variant="text" color="error" aria-label="删除面试" @click.stop="askDelete(session)">
                <Trash2 :size="18" />
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </div>

      <div class="panel">
        <EmptyState v-if="!selected" :icon="FileSearch" title="选择一场面试" description="左侧选择历史场次后，会显示 transcript 与复盘报告。" />
        <template v-else>
          <div class="detail-title">
            <div>
              <h2>#{{ selected.session.id }} {{ selected.session.jd_title || '未关联 JD' }}</h2>
              <p class="muted">{{ selected.session.resume_name || '未关联简历' }} · {{ statusLabel(selected.session.status) }}</p>
            </div>
            <v-btn color="primary" variant="outlined" @click="detailOpen = true">打开详情</v-btn>
          </div>
        </template>
      </div>
    </div>

    <v-dialog v-model="detailOpen" max-width="1120" scrollable>
      <v-card v-if="selected" rounded="lg">
        <v-card-title class="detail-title">
          <div>
            #{{ selected.session.id }} {{ selected.session.jd_title || '未关联 JD' }}
            <div class="text-caption text-medium-emphasis">
              {{ selected.session.resume_name || '未关联简历' }} · {{ statusLabel(selected.session.status) }}
            </div>
          </div>
          <div class="form-actions">
            <v-btn v-if="!selected.report" color="primary" :loading="loading" @click="onFinish(selected.session.id)">
              <Sparkles :size="18" class="mr-2" />生成报告
            </v-btn>
            <v-btn color="error" variant="text" :loading="loading" @click="askDelete(selected.session)">
              <Trash2 :size="18" class="mr-2" />删除
            </v-btn>
          </div>
        </v-card-title>
        <v-card-text>
          <div class="chat history-chat large-history-chat">
            <ChatMessage v-for="message in selected.messages" :key="message.id" :message="message" />
          </div>
          <v-alert v-if="!selected.report" class="mt-4" type="info" variant="tonal">
            这场面试还没有 STAR 复盘报告。
          </v-alert>
          <ReportPanel v-else class="mt-4" :report="selected.report" />
        </v-card-text>
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
import { ref, watch } from 'vue'
import { FileSearch, History, RefreshCw, Sparkles, Trash2 } from 'lucide-vue-next'
import ChatMessage from '../components/ChatMessage.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import ReportPanel from '../components/ReportPanel.vue'

const props = defineProps({
  interviews: { type: Array, required: true },
  selected: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  onRefresh: { type: Function, required: true },
  onSelect: { type: Function, required: true },
  onFinish: { type: Function, required: true },
  onDelete: { type: Function, required: true }
})

const confirmOpen = ref(false)
const pendingDelete = ref(null)
const detailOpen = ref(false)

watch(() => props.selected?.session?.id, (id) => {
  if (id) detailOpen.value = true
})

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
</script>
