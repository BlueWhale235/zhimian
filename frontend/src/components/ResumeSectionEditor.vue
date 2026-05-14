<template>
  <div class="panel">
    <div class="section-head">
      <h2>{{ title }}</h2>
      <v-btn icon variant="tonal" color="primary" :aria-label="`添加${title}`" @click="add">
        <Plus :size="18" />
      </v-btn>
    </div>
    <EmptyState
      v-if="!items.length"
      :icon="FileText"
      :title="`${title}为空`"
      description="添加一条经历后，它会随简历草稿自动保存。"
    />
    <div v-for="(item, index) in items" :key="index" class="section-item">
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field :model-value="item.title" label="标题" variant="outlined" @update:model-value="update(index, 'title', $event)" />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field :model-value="item.meta" label="时间 / 角色 / 学校" variant="outlined" @update:model-value="update(index, 'meta', $event)" />
        </v-col>
      </v-row>
      <v-textarea :model-value="item.description" label="描述" variant="outlined" rows="3" @update:model-value="update(index, 'description', $event)" />
      <div class="item-actions">
        <v-btn icon variant="text" :disabled="index === 0" aria-label="上移" @click="move(index, -1)">
          <ArrowUp :size="18" />
        </v-btn>
        <v-btn icon variant="text" :disabled="index === items.length - 1" aria-label="下移" @click="move(index, 1)">
          <ArrowDown :size="18" />
        </v-btn>
        <v-spacer />
        <v-btn color="error" variant="text" @click="remove(index)">
          <Trash2 :size="18" class="mr-2" />删除
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ArrowDown, ArrowUp, FileText, Plus, Trash2 } from 'lucide-vue-next'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  title: { type: String, required: true },
  items: { type: Array, required: true },
  onChange: { type: Function, required: true }
})

function add() {
  props.onChange([...props.items, { title: '', meta: '', description: '' }])
}

function update(index, key, value) {
  const next = props.items.map((item, i) => i === index ? { ...item, [key]: value } : item)
  props.onChange(next)
}

function remove(index) {
  const next = [...props.items]
  next.splice(index, 1)
  props.onChange(next)
}

function move(index, offset) {
  const next = [...props.items]
  const target = index + offset
  const [item] = next.splice(index, 1)
  next.splice(target, 0, item)
  props.onChange(next)
}
</script>
