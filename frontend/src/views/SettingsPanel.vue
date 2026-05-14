<template>
  <section>
    <PageHeader title="系统设置" subtitle="配置 OpenAI 兼容接口和默认面试参数。" />
    <div class="panel settings-panel">
      <v-alert :type="healthOk ? 'success' : 'error'" variant="tonal" class="mb-4">
        当前后端连接状态：{{ healthOk ? '正常' : '异常' }}
      </v-alert>
      <v-text-field v-model="local.base_url" label="API Base URL" variant="outlined" :error-messages="errors.base_url" />
      <v-text-field
        v-model="local.api_key"
        label="API Key"
        variant="outlined"
        :type="showKey ? 'text' : 'password'"
      >
        <template #append-inner>
          <v-btn icon variant="text" size="small" aria-label="显示或隐藏 API Key" @click="showKey = !showKey">
            <Eye v-if="!showKey" :size="18" />
            <EyeOff v-else :size="18" />
          </v-btn>
        </template>
      </v-text-field>
      <v-text-field v-model="local.model" label="默认模型名称" variant="outlined" :error-messages="errors.model" />
      <v-divider class="my-4" />
      <h3>任务模型</h3>
      <p class="muted mb-4">留空时使用默认模型。可以用便宜模型做 JD 分析，用更强模型做面试和复盘。</p>
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field v-model="local.jd_model" label="JD 分析模型" variant="outlined" placeholder="留空使用默认模型" />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field v-model="local.url_extract_model" label="URL 提取模型" variant="outlined" placeholder="如 qwen3-max-2026-01-23" />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field v-model="local.resume_extract_model" label="简历提取模型" variant="outlined" placeholder="留空使用默认模型" />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field v-model="local.interview_model" label="模拟面试模型" variant="outlined" placeholder="留空使用默认模型" />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field v-model="local.report_model" label="STAR 复盘模型" variant="outlined" placeholder="留空使用默认模型" />
        </v-col>
      </v-row>
      <v-slider v-model="local.max_rounds" label="默认最大轮数" min="1" max="20" step="1" thumb-label />
      <v-slider v-model="local.pressure_level" label="默认压力强度" min="1" max="5" step="1" thumb-label />
      <v-textarea
        v-model="local.normal_interviewer_prompt"
        label="普通面试默认 Prompt"
        variant="outlined"
        rows="6"
        auto-grow
        counter="5000"
      />
      <v-textarea
        v-model="local.pressure_interviewer_prompt"
        label="压力面试默认 Prompt"
        variant="outlined"
        rows="7"
        auto-grow
        counter="5000"
      />
      <div class="form-actions">
        <v-btn variant="outlined" :loading="checking" @click="onCheckHealth">
          <Activity :size="18" class="mr-2" />检查连接
        </v-btn>
        <v-btn color="primary" :loading="loading" @click="save">
          <Save :size="18" class="mr-2" />保存设置
        </v-btn>
      </div>
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { Activity, Eye, EyeOff, Save } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'

const props = defineProps({
  settings: { type: Object, required: true },
  healthOk: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  checking: { type: Boolean, default: false },
  onSave: { type: Function, required: true },
  onCheckHealth: { type: Function, required: true }
})

const showKey = ref(false)
const errors = reactive({ base_url: '', model: '' })
const local = reactive({
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

watch(() => props.settings, (value) => Object.assign(local, value), { immediate: true, deep: true })

function save() {
  errors.base_url = ''
  errors.model = ''
  if (!/^https?:\/\//.test(local.base_url || '')) errors.base_url = '请输入 http 或 https 开头的地址'
  if (!local.model?.trim()) errors.model = '模型名称不能为空'
  if (errors.base_url || errors.model) return
  props.onSave({ ...local })
}
</script>
