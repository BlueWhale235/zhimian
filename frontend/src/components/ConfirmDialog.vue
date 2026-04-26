<template>
  <v-dialog :model-value="modelValue" max-width="420" @update:model-value="$emit('update:modelValue', $event)">
    <v-card rounded="lg">
      <v-card-title>{{ title }}</v-card-title>
      <v-card-text class="text-body-2 text-medium-emphasis">{{ message }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="$emit('update:modelValue', false)">取消</v-btn>
        <v-btn :color="color" variant="flat" @click="$emit('confirm')">{{ confirmText }}</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, required: true },
  title: { type: String, default: '确认操作' },
  message: { type: String, default: '确定继续吗？' },
  confirmText: { type: String, default: '确认' },
  color: { type: String, default: 'error' }
})

defineEmits(['update:modelValue', 'confirm'])
</script>
