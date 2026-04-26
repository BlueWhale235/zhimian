<template>
  <v-overlay :model-value="modelValue" class="align-center justify-center" persistent>
    <v-progress-circular indeterminate color="primary" size="42" />
  </v-overlay>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false }
})
</script>
