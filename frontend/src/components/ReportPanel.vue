<template>
  <div v-if="report" class="report-grid">
    <div class="panel">
      <h3>综合评价</h3>
      <p>{{ report.summary || '暂无评价' }}</p>
    </div>
    <div class="panel">
      <h3>STAR 优化</h3>
      <div v-if="starItems.length" class="stack">
        <v-card v-for="(item, index) in starItems" :key="index" rounded="lg" variant="tonal">
          <v-card-text>
            <div v-if="typeof item === 'string'">{{ item }}</div>
            <div v-else>
              <p v-for="(value, key) in item" :key="key"><strong>{{ key }}：</strong>{{ value }}</p>
            </div>
          </v-card-text>
        </v-card>
      </div>
      <p v-else class="muted">暂无 STAR 重构。</p>
    </div>
    <div class="panel">
      <h3>闪光点</h3>
      <div class="chip-row">
        <v-chip v-for="item in highlights" :key="item" class="report-chip" color="secondary" variant="tonal">{{ item }}</v-chip>
        <span v-if="!highlights.length" class="muted">暂无</span>
      </div>
    </div>
    <div class="panel">
      <h3>需要改进</h3>
      <div class="chip-row">
        <v-chip v-for="item in improvements" :key="item" class="report-chip" color="warning" variant="tonal">{{ item }}</v-chip>
        <span v-if="!improvements.length" class="muted">暂无</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, default: null }
})

const starItems = computed(() => props.report?.star || [])
const highlights = computed(() => props.report?.highlights || [])
const improvements = computed(() => props.report?.improvements || [])
</script>
