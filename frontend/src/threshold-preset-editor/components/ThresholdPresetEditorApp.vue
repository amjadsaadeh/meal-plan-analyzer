<template>
  <div class="preset-editor-container">
    <!-- Back link -->
    <a :href="presetListUrl" class="back-link">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
      {{ i18n.backToList }}
    </a>

    <!-- Autosave indicator -->
    <div
      class="autosave-indicator"
      :class="saveStatus"
      v-show="saveStatus !== 'idle'"
    >
      <span v-if="saveStatus === 'saving'">{{ i18n.saving }}</span>
      <span v-else-if="saveStatus === 'saved'">{{ i18n.saved }}</span>
      <span v-else-if="saveStatus === 'error'">{{ i18n.errorSaving }}</span>
    </div>

    <div v-if="notFound" class="error-msg">{{ i18n.notFound }}</div>

    <template v-else-if="preset">
      <!-- Name header -->
      <div class="preset-header">
        <template v-if="!editingName">
          <h1 class="preset-name-display">{{ preset.name }}</h1>
          <button class="btn-edit-name" @click="startEditName">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round"
                 stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
          </button>
        </template>
        <template v-else>
          <input
            ref="nameInputEl"
            class="name-input"
            v-model="editName"
            @blur="saveName"
            @keydown.enter="nameInputEl?.blur()"
            @keydown.escape="cancelEditName"
          />
        </template>
      </div>

      <!-- Nutrient card -->
      <div class="nutrient-card">
        <div class="nutrient-rows">
          <div
            v-for="nutrient in nutrients"
            :key="nutrient.key"
            class="nutrient-row"
          >
            <div class="nutrient-row-main">
            <div class="nutrient-label">
              {{ nutrient.label }}
              <span class="nutrient-unit">({{ nutrient.unit }})</span>
            </div>
            <div class="nutrient-inputs">
              <span class="input-label">{{ i18n.min }}</span>
              <div class="input-wrapper">
                <input
                  class="nutrient-min-input threshold-input"
                  :class="{ 'input-error': fieldErrors[nutrient.key + '_min'] }"
                  type="number"
                  step="any"
                  :value="pendingValues[nutrient.key + '_min'] ?? preset[nutrient.key + '_min'] ?? ''"
                  @input="onFieldInput(nutrient.key + '_min', ($event.target as HTMLInputElement).value)"
                  @blur="saveField(nutrient.key + '_min', ($event.target as HTMLInputElement).value)"
                  :placeholder="i18n.min"
                />
              </div>
              <span class="input-label">{{ i18n.max }}</span>
              <div class="input-wrapper">
                <input
                  class="nutrient-max-input threshold-input"
                  :class="{ 'input-error': fieldErrors[nutrient.key + '_max'] }"
                  type="number"
                  step="any"
                  :value="pendingValues[nutrient.key + '_max'] ?? preset[nutrient.key + '_max'] ?? ''"
                  @input="onFieldInput(nutrient.key + '_max', ($event.target as HTMLInputElement).value)"
                  @blur="saveField(nutrient.key + '_max', ($event.target as HTMLInputElement).value)"
                  :placeholder="i18n.max"
                />
              </div>
            </div>
            </div><!-- nutrient-row-main -->
            <div class="field-error-msg">
              {{ fieldErrors[nutrient.key + '_min'] || fieldErrors[nutrient.key + '_max'] || '\u00a0' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Delete -->
      <div class="danger-zone">
        <button class="btn-danger" @click="deletePreset">
          {{ i18n.deletePreset }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, onMounted, nextTick } from 'vue'
import type { ThresholdPreset, Nutrient, I18n } from '../../types/index'

const presetId = inject<string>('presetId')!
const csrfToken = inject<string>('csrfToken')!
const nutrients = inject<Nutrient[]>('nutrients')!
const i18n = inject<I18n>('i18n')!
const presetListUrl = inject<string>('presetListUrl')!

const preset = ref<ThresholdPreset | null>(null)
const notFound = ref(false)
const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const editingName = ref(false)
const editName = ref('')
const nameInputEl = ref<HTMLInputElement | null>(null)
const fieldErrors = ref<Record<string, string>>({})
const pendingValues = ref<Record<string, string>>({})

async function loadPreset() {
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`)
    if (res.status === 404) {
      notFound.value = true
      return
    }
    if (!res.ok) throw new Error(String(res.status))
    preset.value = await res.json()
  } catch (e) {
    notFound.value = true
  }
}

async function patch(data: Record<string, unknown>) {
  saveStatus.value = 'saving'
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(String(res.status))
    const responseData: ThresholdPreset = await res.json()
    for (const key of Object.keys(data)) {
      preset.value![key] = responseData[key]
    }
    saveStatus.value = 'saved'
    setTimeout(() => {
      if (saveStatus.value === 'saved') saveStatus.value = 'idle'
    }, 2000)
  } catch (e) {
    saveStatus.value = 'error'
  }
}

function validateField(fieldName: string, rawValue: string | null | undefined): string | null {
  if (rawValue === '' || rawValue === null || rawValue === undefined) {
    return null
  }
  const val = parseFloat(rawValue)
  if (isNaN(val)) {
    return i18n.mustBeValidNumber
  }
  if (fieldName.endsWith('_min')) {
    const maxField = fieldName.slice(0, -4) + '_max'
    const maxVal = preset.value?.[maxField] as number | null | undefined
    if (maxVal !== null && maxVal !== undefined && val >= maxVal) {
      return i18n.mustBeLessThanMax.replace('{max}', String(maxVal))
    }
  } else if (fieldName.endsWith('_max')) {
    const minField = fieldName.slice(0, -4) + '_min'
    const minVal = preset.value?.[minField] as number | null | undefined
    if (minVal !== null && minVal !== undefined && val <= minVal) {
      return i18n.mustBeGreaterThanMin.replace('{min}', String(minVal))
    }
  }
  return null
}

function onFieldInput(fieldName: string, rawValue: string) {
  // Track the pending value so the input is not reset while the user is typing
  pendingValues.value = { ...pendingValues.value, [fieldName]: rawValue }
}

function clearPending(fieldName: string) {
  const updated = { ...pendingValues.value }
  delete updated[fieldName]
  pendingValues.value = updated
}

async function saveField(fieldName: string, rawValue: string) {
  const error = validateField(fieldName, rawValue)
  if (error) {
    fieldErrors.value = { ...fieldErrors.value, [fieldName]: error }
    // Keep pendingValues so the input retains the typed value on re-render
    return
  }

  const newErrors = { ...fieldErrors.value }
  delete newErrors[fieldName]
  fieldErrors.value = newErrors

  const value = rawValue === '' ? null : parseFloat(rawValue)

  // Only patch if the value has actually changed from the saved state
  const currentValue = (preset.value?.[fieldName] ?? null) as number | null
  if (value === currentValue) {
    // No change — just clear the pending value, no network request needed
    clearPending(fieldName)
    return
  }

  // Clear the pending value — the server value will take over after the patch
  clearPending(fieldName)

  await patch({ [fieldName]: value })

  // After a successful save, re-check the partner field to clear stale errors
  const partnerSuffix = fieldName.endsWith('_min') ? '_max' : '_min'
  const partnerField = fieldName.slice(0, -4) + partnerSuffix
  if (fieldErrors.value[partnerField]) {
    const partnerVal = preset.value?.[partnerField] as number | null | undefined
    const partnerError =
      partnerVal !== null && partnerVal !== undefined
        ? validateField(partnerField, String(partnerVal))
        : null
    if (!partnerError) {
      const cleared = { ...fieldErrors.value }
      delete cleared[partnerField]
      fieldErrors.value = cleared
      clearPending(partnerField)
    }
  }
}

function startEditName() {
  editName.value = preset.value?.name ?? ''
  editingName.value = true
  nextTick(() => nameInputEl.value?.focus())
}

function cancelEditName() {
  editingName.value = false
}

async function saveName() {
  const name = editName.value.trim()
  editingName.value = false
  if (!name || name === preset.value?.name) return
  await patch({ name })
}

async function deletePreset() {
  if (!window.confirm(i18n.deleteConfirm)) return
  saveStatus.value = 'saving'
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': csrfToken },
    })
    if (!res.ok) throw new Error(String(res.status))
    window.location.href = presetListUrl
  } catch (e) {
    saveStatus.value = 'error'
  }
}

onMounted(loadPreset)
</script>

<style scoped>
.input-wrapper {
  display: inline-flex;
  flex-direction: column;
}

.input-error {
  border-color: var(--danger) !important;
  outline-color: var(--danger);
}

.input-error:focus {
  box-shadow: 0 0 0 2px var(--danger-glow);
}

.field-error-msg {
  font-size: 0.72rem;
  color: var(--danger);
  line-height: 1.2;
}
</style>
