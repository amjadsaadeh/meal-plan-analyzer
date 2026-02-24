<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseInput from '../ui/BaseInput.vue'
import { useDebounce } from '../../composables/useDebounce'

const { t } = useI18n()

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  search: [value: string]
}>()

const localValue = ref(props.modelValue)
const debounced = useDebounce(localValue)

watch(debounced, value => {
  emit('update:modelValue', value)
  emit('search', value)
})

watch(() => props.modelValue, v => {
  if (v !== localValue.value) localValue.value = v
})
</script>

<template>
  <BaseInput
    id="liveSearch"
    v-model="localValue"
    :placeholder="t('searchPlansPlaceholder')"
  />
</template>
