<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import BaseModal from '../ui/BaseModal.vue'

const { t } = useI18n()

defineProps<{ open: boolean }>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <BaseModal
    :open="open"
    :confirm-label="t('delete')"
    :cancel-label="t('cancel')"
    confirm-variant="danger"
    @confirm="emit('confirm')"
    @cancel="emit('cancel')"
  >
    <p>{{ t('confirmDeletePlan') }}</p>
  </BaseModal>
</template>
