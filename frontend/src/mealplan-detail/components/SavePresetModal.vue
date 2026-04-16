<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="modal-overlay active"
        @click.self="$emit('cancel')"
      >
        <div
          class="modal-content"
          role="dialog"
          aria-modal="true"
          @keydown.esc="$emit('cancel')"
        >
          <div class="modal-header">{{ i18n.saveTemplate }}</div>
          <div class="modal-body">
            <input
              ref="nameInputEl"
              type="text"
              class="modal-input"
              :placeholder="i18n.templateName"
              autocomplete="off"
              v-model="nameVal"
              @input="onInput"
              @keydown.enter="onEnter"
              @keydown.esc="$emit('cancel')"
            >
            <div class="modal-error">{{ errorMsg }}</div>
          </div>
          <div class="modal-actions">
            <button class="btn-modal btn-modal-cancel" @click="$emit('cancel')">{{ i18n.cancel }}</button>
            <button
              class="btn-modal btn-modal-save"
              :disabled="saveDisabled"
              @click="onSave"
            >{{ i18n.saveTemplate }}</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, inject } from 'vue'
import type { I18n, ThresholdMap, Nutrient, ThresholdPreset } from '../../types/index'

const i18n = inject<I18n>('i18n')!

const props = withDefaults(defineProps<{
  open: boolean
  thresholds?: ThresholdMap
  nutrients?: Nutrient[]
}>(), {
  thresholds: () => ({}),
  nutrients: () => [],
})

const emit = defineEmits<{
  confirm: [name: string]
  cancel: []
}>()

const nameInputEl = ref<HTMLInputElement | null>(null)
const nameVal = ref('')
const errorMsg = ref('')
const saveDisabled = ref(true)
let nameTimer: ReturnType<typeof setTimeout> | null = null

watch(() => props.open, async (val) => {
  if (val) {
    nameVal.value = ''
    errorMsg.value = ''
    saveDisabled.value = true
    await nextTick()
    nameInputEl.value?.focus()
  }
})

function onInput() {
  const val = nameVal.value.trim()
  saveDisabled.value = true
  if (val.length < 3) {
    errorMsg.value = i18n.nameTooShort
    return
  }
  errorMsg.value = i18n.checkingAvailability
  clearTimeout(nameTimer ?? undefined)
  nameTimer = setTimeout(() => validateName(val), 500)
}

async function validateName(name: string) {
  try {
    const res = await fetch(`/api/threshold-presets/?search=${encodeURIComponent(name)}`)
    const data: { results?: ThresholdPreset[] } = await res.json()
    const presets = data.results || []
    const exactMatch = presets.find(p => (p.name as string).toLowerCase() === name.toLowerCase())
    if (exactMatch) {
      errorMsg.value = i18n.nameAlreadyTaken
      saveDisabled.value = true
    } else {
      errorMsg.value = ''
      saveDisabled.value = false
    }
  } catch (e) {
    errorMsg.value = i18n.validationError
  }
}

function onEnter() {
  if (!saveDisabled.value) onSave()
}

function onSave() {
  const name = nameVal.value.trim()
  if (name.length < 3 || saveDisabled.value) return
  emit('confirm', name)
}
</script>
