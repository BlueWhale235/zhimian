<template>
  <v-card rounded="lg" variant="outlined" class="resume-card">
    <div class="thumb">
      <v-img v-if="resume.thumbnail_path_url" :src="assetUrl(resume.thumbnail_path_url)" height="260" cover />
      <div v-else class="thumb-placeholder">
        <FileText :size="42" />
        <span>PDF</span>
      </div>
    </div>
    <v-card-title class="text-subtitle-1">{{ resume.original_name }}</v-card-title>
    <v-card-subtitle>{{ sourceLabel }} · {{ resume.created_at }}</v-card-subtitle>
    <v-card-actions>
      <v-btn icon variant="text" aria-label="预览" @click="$emit('preview', resume)">
        <Eye :size="18" />
      </v-btn>
      <v-btn icon variant="text" :href="assetUrl(resume.file_path_url)" download aria-label="下载">
        <Download :size="18" />
      </v-btn>
      <v-spacer />
      <v-btn icon color="error" variant="text" aria-label="删除" @click="$emit('delete', resume)">
        <Trash2 :size="18" />
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { Download, Eye, FileText, Trash2 } from 'lucide-vue-next'
import { assetUrl } from '../api'

const props = defineProps({
  resume: { type: Object, required: true }
})

defineEmits(['preview', 'delete'])

const sourceLabel = computed(() => props.resume.source_type === 'generated' ? '在线生成' : '上传')
</script>
