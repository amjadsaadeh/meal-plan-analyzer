<script setup lang="ts">
defineProps<{
  open: boolean
  confirmLabel?: string
  cancelLabel?: string
  confirmVariant?: 'primary' | 'secondary' | 'danger'
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-backdrop" @click.self="emit('cancel')">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-body">
          <slot />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="emit('cancel')">
            {{ cancelLabel ?? 'Cancel' }}
          </button>
          <button
            class="btn"
            :class="`btn-${confirmVariant ?? 'danger'}`"
            data-testid="confirm-delete-btn"
            @click="emit('confirm')"
          >
            {{ confirmLabel ?? 'Confirm' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
