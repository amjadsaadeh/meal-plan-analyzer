<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        id="deleteDayModal"
        class="modal-overlay active"
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
            <button id="confirmDeleteDayBtn" class="btn-danger" @click="$emit('confirm')">{{ i18n.delete }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, inject } from 'vue'
import type { I18n } from '../../types/index'

const i18n = inject<I18n>('i18n')!

const props = withDefaults(defineProps<{
  open: boolean
  dayName?: string
}>(), {
  dayName: '',
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
