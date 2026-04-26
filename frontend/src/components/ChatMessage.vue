<template>
  <div class="message-row" :class="message.role">
    <div class="message-meta">
      <span>{{ message.role === 'assistant' ? '面试官' : '候选人' }}</span>
      <span v-if="message.created_at">{{ message.created_at }}</span>
    </div>
    <div class="bubble" :class="message.role">{{ message.content }}</div>
  </div>
</template>

<script setup>
defineProps({
  message: { type: Object, required: true }
})
</script>
