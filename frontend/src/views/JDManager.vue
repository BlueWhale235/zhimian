<template>
  <section>
    <PageHeader title="JD 管理" subtitle="粘贴目标岗位描述，系统会尝试提取技能要求">
      <template #actions>
        <v-btn color="primary" @click="openCreate">
          <Plus :size="18" class="mr-2" />新增 JD
        </v-btn>
      </template>
    </PageHeader>

    <div class="jd-list">
      <EmptyState v-if="!jds.length" :icon="BriefcaseBusiness" title="还没有JD" description="点击右上角新增 JD，可手动粘贴，也可从支持网页工具的模型中提取。" />
      <JDCard
        v-for="jd in jds"
        v-else
        :key="jd.id"
        :jd="jd"
        :selected="selected?.id === jd.id"
        :on-select="selectJd"
        :on-extract="extractJd"
        :on-delete="askDelete"
      />
    </div>

    <v-dialog v-model="createOpen" max-width="900" scrollable>
      <v-card rounded="lg">
        <v-card-title class="detail-title">
          新增 JD
          <v-btn icon variant="text" aria-label="关闭" @click="createOpen = false">
            <X :size="18" />
          </v-btn>
        </v-card-title>
        <v-card-text>
          <div class="url-extract-row">
            <v-text-field v-model="url" label="招聘页面 URL" variant="outlined" hide-details />
            <v-btn color="secondary" :loading="extracting" :disabled="!url.trim()" @click="extractFromUrl">
              <Sparkles :size="18" class="mr-2" />提取
            </v-btn>
          </div>
          <v-divider class="my-5" />
          <v-text-field v-model="form.title" label="岗位名称" variant="outlined" />
          <v-text-field v-model="form.company" label="公司" variant="outlined" />
          <v-textarea v-model="form.company_background" label="公司背景简介" variant="outlined" rows="4" auto-grow />
          <v-textarea v-model="form.content" label="职位描述" variant="outlined" rows="12" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="createOpen = false">取消</v-btn>
          <v-btn color="primary" :loading="loading" @click="create">
            <Plus :size="18" class="mr-2" />保存 JD
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
          <h3>公司背景</h3>
          <v-textarea v-model="detailForm.company_background" label="公司背景简介" variant="outlined" rows="5" auto-grow />
          <v-btn class="mb-4" variant="outlined" color="primary" :loading="loading" @click="saveSelected">
            保存背景信息
          </v-btn>
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
      :model-value="confirmOpen"
      title="删除 JD"
      :message="`确定删除「${pendingDelete?.title || ''}」吗？历史面试不会被删除。`"
      confirm-text="删除"
      :on-change="value => { confirmOpen = value }"
      :on-confirm="confirmDelete"
    />
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { BriefcaseBusiness, Plus, Sparkles, X } from 'lucide-vue-next'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import EmptyState from '../components/EmptyState.vue'
import JDCard from '../components/JDCard.vue'
import PageHeader from '../components/PageHeader.vue'

const props = defineProps({
  jds: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  extractUrl: { type: Function, default: null },
  onCreate: { type: Function, required: true },
  onUpdate: { type: Function, required: true },
  onExtract: { type: Function, required: true },
  onDelete: { type: Function, required: true },
  onToast: { type: Function, required: true }
})

const emptyForm = () => ({ title: '', company: '', company_background: '', content: '' })
const form = reactive(emptyForm())
const detailForm = reactive({ company_background: '' })
const selected = ref(null)
const pendingDelete = ref(null)
const confirmOpen = ref(false)
const createOpen = ref(false)
const extracting = ref(false)
const url = ref('')

const detailOpen = computed({
  get: () => Boolean(selected.value),
  set: (value) => {
    if (!value) selected.value = null
  }
})

function openCreate() {
  Object.assign(form, emptyForm())
  url.value = ''
  createOpen.value = true
}

async function extractFromUrl() {
  if (!props.extractUrl) return
  extracting.value = true
  try {
    const data = await props.extractUrl(url.value.trim())
    if (!data) return
    Object.assign(form, {
      title: data.title || form.title,
      company: data.company || form.company,
      company_background: data.company_background || form.company_background,
      content: data.content || form.content
    })
  } finally {
    extracting.value = false
  }
}

function create() {
  if (!form.title.trim() || !form.content.trim()) {
    props.onToast('请填写岗位名称和职位描述。', 'warning')
    return
  }
  props.onCreate({ ...form })
  createOpen.value = false
  Object.assign(form, emptyForm())
}

function saveSelected() {
  if (!selected.value) return
  props.onUpdate({
    ...selected.value,
    company_background: detailForm.company_background
  })
  selected.value.company_background = detailForm.company_background
}

watch(selected, (value) => {
  detailForm.company_background = value?.company_background || ''
})

function askDelete(jd) {
  pendingDelete.value = jd
  confirmOpen.value = true
}

function confirmDelete() {
  if (pendingDelete.value) props.onDelete(pendingDelete.value.id)
  if (selected.value?.id === pendingDelete.value?.id) selected.value = null
  confirmOpen.value = false
}

function selectJd(jd) {
  selected.value = jd
}

function extractJd(jd) {
  props.onExtract(jd.id)
}
</script>
