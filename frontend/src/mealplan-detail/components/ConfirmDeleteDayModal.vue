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
          tabindex="-1"
          @keydown.esc="$emit('cancel')"
        >
          <div class="modal-header">
            <h3>{{ i18n.deleteDay }}</h3>
          </div>
          <div class="modal-body">
            <p>{{ i18n.confirmDeleteDay }} "<strong style="color: var(--text-main);">{{ dayName }}</strong>"?</p>
            <p class="modal-warning">{{ i18n.cannotBeUndone }}</p>
          </div>
          <div class="modal-footer">
            <button ref="cancelBtnRef" class="btn-secondary" style="margin-top: 0;" @click="$emit('cancel')">{{ i18n.cancel }}</button>
            <button class="btn-danger" @click="$emit('confirm')">{{ i18n.delete }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, nextTick, inject } from 'vue'

const i18n = inject('i18n')

const props = defineProps({
  open: { type: Boolean, required: true },
  dayName: { type: String, default: '' },
})

defineEmits(['confirm', 'cancel'])

const cardRef = ref(null)
const cancelBtnRef = ref(null)

watch(() => props.open, async (val) => {
  if (val) {
    await nextTick()
    cancelBtnRef.value?.focus()
  }
})
</script>
