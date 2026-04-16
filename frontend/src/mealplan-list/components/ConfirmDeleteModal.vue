<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="modal-overlay"
        @click.self="$emit('cancel')"
      >
        <div
          ref="cardRef"
          class="modal-card"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          aria-describedby="modal-desc"
          tabindex="-1"
          @keydown.esc="$emit('cancel')"
        >
          <div class="modal-icon-wrap">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
          </div>

          <h2 id="modal-title" class="modal-title">{{ title }}</h2>

          <div id="modal-desc" class="modal-body">
            <p class="modal-plan-name">{{ planName }}</p>
            <p class="modal-message">{{ message }}</p>
            <p class="modal-hint">{{ hint }}</p>
          </div>

          <div class="modal-actions">
            <button ref="cancelBtnRef" class="btn-modal-cancel" @click="$emit('cancel')">
              {{ cancelText }}
            </button>
            <button class="btn-modal-delete" @click="$emit('confirm')">
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = withDefaults(defineProps<{
  open: boolean
  planName?: string
  title?: string
  message?: string
  hint?: string
  cancelText?: string
  confirmText?: string
}>(), {
  planName: '',
  title: 'Delete Meal Plan',
  message: 'Are you sure you want to delete this meal plan?',
  hint: 'This action cannot be undone.',
  cancelText: 'Cancel',
  confirmText: 'Delete',
})

defineEmits<{
  confirm: []
  cancel: []
}>()

const cardRef = ref<HTMLDivElement | null>(null)
const cancelBtnRef = ref<HTMLButtonElement | null>(null)

watch(() => props.open, async (val) => {
  if (val) {
    await nextTick()
    cancelBtnRef.value?.focus()
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-card {
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  padding: 2rem;
  max-width: 420px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  outline: none;
}

.modal-icon-wrap {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(166, 65, 67, 0.1);
  color: var(--danger);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.modal-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 0;
  text-align: center;
}

.modal-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  text-align: center;
}

.modal-plan-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-main);
  background: rgba(106, 217, 198, 0.1);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  padding: 0.4rem 1rem;
  margin: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-message {
  font-size: 0.9rem;
  color: var(--text-dim);
  margin: 0;
}

.modal-hint {
  font-size: 0.8rem;
  color: var(--text-dim);
  margin: 0;
  opacity: 0.8;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
  width: 100%;
}

.btn-modal-cancel,
.btn-modal-delete {
  flex: 1;
  padding: 0.65rem 1rem;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 400;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--glass-border);
}

.btn-modal-cancel {
  background: transparent;
  color: var(--text-main);
}

.btn-modal-cancel:hover {
  background: rgba(0, 0, 0, 0.04);
}

.btn-modal-delete {
  background: var(--danger);
  color: white;
  border-color: var(--danger);
}

.btn-modal-delete:hover {
  background: #8a3436;
  border-color: #8a3436;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(166, 65, 67, 0.3);
}

/* Overlay fade */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* Card slide-up */
.modal-enter-active .modal-card,
.modal-leave-active .modal-card {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.modal-enter-from .modal-card,
.modal-leave-to .modal-card {
  transform: translateY(16px) scale(0.97);
  opacity: 0;
}
</style>
