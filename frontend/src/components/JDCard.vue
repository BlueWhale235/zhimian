<template>
  <v-card rounded="lg" variant="outlined" :class="{ selected }">
    <v-card-title class="d-flex align-center ga-2">
      <span>{{ jd.title }}</span>
      <v-chip v-if="jd.requirements?.seniority" size="x-small" color="secondary" variant="tonal">
        {{ jd.requirements.seniority }}
      </v-chip>
    </v-card-title>
    <v-card-subtitle>{{ jd.company || '未填写公司' }} · {{ jd.created_at }}</v-card-subtitle>
    <v-card-text>
      <div class="chip-row">
        <v-chip v-for="skill in skills" :key="skill" size="small">{{ skill }}</v-chip>
        <span v-if="!skills.length" class="muted">暂无技能标签</span>
      </div>
      <p class="muted mt-3">{{ jd.content.slice(0, 140) }}{{ jd.content.length > 140 ? '...' : '' }}</p>
    </v-card-text>
    <v-card-actions>
      <v-btn variant="text" color="primary" @click="$emit('select', jd)">查看详情</v-btn>
      <v-btn icon variant="text" color="primary" aria-label="重新提取" @click="$emit('extract', jd)">
        <Sparkles :size="18" />
      </v-btn>
      <v-spacer />
      <v-btn icon variant="text" color="error" aria-label="删除" @click="$emit('delete', jd)">
        <Trash2 :size="18" />
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { Sparkles, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  jd: { type: Object, required: true },
  selected: { type: Boolean, default: false }
})

defineEmits(['select', 'extract', 'delete'])

const skills = computed(() => props.jd.requirements?.skills || [])
</script>
