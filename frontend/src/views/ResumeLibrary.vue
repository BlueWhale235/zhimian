<template>
  <section>
    <PageHeader title="简历库" subtitle="上传 PDF 简历，系统会生成首页缩略图并保存相对路径。">
      <template #actions>
        <input ref="fileInput" class="hidden-input" type="file" accept="application/pdf" @change="onNativePick" />
        <v-btn color="primary" :loading="loading" @click="fileInput?.click()">
          <UploadCloud :size="18" class="mr-2" />上传 PDF
        </v-btn>
      </template>
    </PageHeader>

    <div
      class="upload-zone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <UploadCloud :size="26" />
      <span>拖拽 PDF 到这里，或使用右上角按钮上传</span>
    </div>

    <EmptyState
      v-if="!resumes.length"
      :icon="FileText"
      title="还没有简历"
      description="上传一份 PDF 简历，或在在线构建器里导出一份。"
    />
    <div v-else class="grid">
      <ResumeCard
        v-for="resume in resumes"
        :key="resume.id"
        :resume="resume"
        :on-preview="openPreview"
        :on-delete="askDelete"
      />
    </div>

    <v-dialog v-model="previewOpen" max-width="980" height="86vh">
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center">
          {{ preview?.original_name }}
          <v-spacer />
          <v-btn icon variant="text" aria-label="关闭" @click="preview = null">
            <X :size="18" />
          </v-btn>
        </v-card-title>
        <v-card-text class="pdf-frame-wrap">
          <iframe v-if="preview" class="pdf-frame" :src="assetUrl(preview.file_path_url)" />
        </v-card-text>
        <v-expansion-panels v-if="preview" class="resume-text-panel" variant="accordion">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <div class="section-head resume-text-title">
                <span>提取出来的简历文本</span>
                <v-chip :color="preview.has_parsed_text ? 'success' : 'warning'" size="small" variant="tonal">
                  {{ preview.has_parsed_text ? '已有有效文本' : '文本不足' }}
                </v-chip>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <div class="form-actions mb-3">
                <v-btn color="primary" variant="outlined" :loading="loading" @click="extractPreviewText">
                  <Sparkles :size="18" class="mr-2" />AI 提取/重提取
                </v-btn>
                <span class="muted">扫描件或本地抽取效果不好时再使用，会消耗模型额度。</span>
              </div>
              <pre class="resume-text-preview">{{ preview.parsed_text || '暂无提取文本。可以点击 AI 提取，或检查 PDF 是否为扫描件。' }}</pre>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card>
    </v-dialog>

    <ConfirmDialog
      :model-value="confirmOpen"
      title="删除简历"
      :message="`确定删除「${pendingDelete?.original_name || ''}」吗？文件和缩略图也会被清理。`"
      confirm-text="删除"
      :on-change="value => { confirmOpen = value }"
      :on-confirm="confirmDelete"
    />
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { FileText, Sparkles, UploadCloud, X } from 'lucide-vue-next'
import { assetUrl } from '../api'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import ResumeCard from '../components/ResumeCard.vue'

const props = defineProps({
  resumes: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  onUpload: { type: Function, required: true },
  onDelete: { type: Function, required: true },
  onExtractText: { type: Function, required: true },
  onToast: { type: Function, required: true }
})

const fileInput = ref(null)
const dragging = ref(false)
const preview = ref(null)
const pendingDelete = ref(null)
const confirmOpen = ref(false)
const previewOpen = computed({
  get: () => Boolean(preview.value),
  set: (value) => {
    if (!value) preview.value = null
  }
})

function normalizeFile(input) {
  return Array.isArray(input) ? input[0] : input
}

function submit(candidate) {
  const selected = normalizeFile(candidate)
  if (!selected) return
  if (selected.type !== 'application/pdf' && !selected.name?.toLowerCase().endsWith('.pdf')) {
    props.onToast('仅支持上传 PDF 文件。', 'warning')
    return
  }
  props.onUpload(selected)
}

function onNativePick(event) {
  submit(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  dragging.value = false
  submit(event.dataTransfer.files?.[0])
}

function askDelete(resume) {
  pendingDelete.value = resume
  confirmOpen.value = true
}

function confirmDelete() {
  if (pendingDelete.value) props.onDelete(pendingDelete.value.id)
  confirmOpen.value = false
}

function extractPreviewText() {
  if (!preview.value) return
  props.onExtractText(preview.value.id)
}

function openPreview(resume) {
  preview.value = resume
}

watch(() => props.resumes, (items) => {
  if (!preview.value) return
  const updated = items.find(item => item.id === preview.value.id)
  if (updated) preview.value = updated
}, { deep: true })
</script>
