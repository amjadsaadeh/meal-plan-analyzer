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
            @keydown.enter="nameInputEl.blur()"
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
            <span class="nutrient-label">
              {{ nutrient.label }}
              <span class="nutrient-unit">({{ nutrient.unit }})</span>
            </span>
            <div class="nutrient-inputs">
              <span class="input-label">{{ i18n.min }}</span>
              <div class="input-wrapper">
                <input
                  class="nutrient-min-input threshold-input"
                  :class="{ 'input-error': fieldErrors[nutrient.key + '_min'] }"
                  type="number"
                  step="any"
                  :value="preset[nutrient.key + '_min'] ?? ''"
                  @blur="saveField(nutrient.key + '_min', $event.target.value)"
                  @mouseenter="hoveredField = nutrient.key + '_min'"
                  @mouseleave="hoveredField = null"
                  :placeholder="i18n.min"
                />
                <div
                  v-if="hoveredField === nutrient.key + '_min' && fieldErrors[nutrient.key + '_min']"
                  class="error-tooltip"
                >
                  {{ fieldErrors[nutrient.key + '_min'] }}
                </div>
              </div>
              <span class="input-label">{{ i18n.max }}</span>
              <div class="input-wrapper">
                <input
                  class="nutrient-max-input threshold-input"
                  :class="{ 'input-error': fieldErrors[nutrient.key + '_max'] }"
                  type="number"
                  step="any"
                  :value="preset[nutrient.key + '_max'] ?? ''"
                  @blur="saveField(nutrient.key + '_max', $event.target.value)"
                  @mouseenter="hoveredField = nutrient.key + '_max'"
                  @mouseleave="hoveredField = null"
                  :placeholder="i18n.max"
                />
                <div
                  v-if="hoveredField === nutrient.key + '_max' && fieldErrors[nutrient.key + '_max']"
                  class="error-tooltip"
                >
                  {{ fieldErrors[nutrient.key + '_max'] }}
                </div>
              </div>
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

<script setup>
import { ref, inject, onMounted, nextTick } from 'vue'

const presetId = inject('presetId')
const csrfToken = inject('csrfToken')
const nutrients = inject('nutrients')
const i18n = inject('i18n')
const presetListUrl = inject('presetListUrl')

const preset = ref(null)
const notFound = ref(false)
const saveStatus = ref('idle')
const editingName = ref(false)
const editName = ref('')
const nameInputEl = ref(null)
const fieldErrors = ref({})
const hoveredField = ref(null)

async function loadPreset() {
  try {
    const res = await fetch(`/api/threshold-presets/${presetId}/`)
    if (res.status === 404) {
      notFound.value = true
      return
    }
    if (!res.ok) throw new Error(res.status)
    preset.value = await res.json()
  } catch (e) {
    notFound.value = true
  }
}

async function patch(data) {
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
    if (!res.ok) throw new Error(res.status)
    const responseData = await res.json()
    for (const key of Object.keys(data)) {
      preset.value[key] = responseData[key]
    }
    saveStatus.value = 'saved'
    setTimeout(() => {
      if (saveStatus.value === 'saved') saveStatus.value = 'idle'
    }, 2000)
  } catch (e) {
    saveStatus.value = 'error'
  }
}

function validateField(fieldName, rawValue) {
  if (rawValue === '' || rawValue === null || rawValue === undefined) {
    return null
  }
  const val = parseFloat(rawValue)
  if (isNaN(val)) {
    return i18n.mustBeValidNumber
  }
  if (fieldName.endsWith('_min')) {
    const maxField = fieldName.slice(0, -4) + '_max'
    const maxVal = preset.value?.[maxField]
    if (maxVal !== null && maxVal !== undefined && val >= maxVal) {
      return i18n.mustBeLessThanMax.replace('{max}', maxVal)
    }
  } else if (fieldName.endsWith('_max')) {
    const minField = fieldName.slice(0, -4) + '_min'
    const minVal = preset.value?.[minField]
    if (minVal !== null && minVal !== undefined && val <= minVal) {
      return i18n.mustBeGreaterThanMin.replace('{min}', minVal)
    }
  }
  return null
}

async function saveField(fieldName, rawValue) {
  const error = validateField(fieldName, rawValue)
  if (error) {
    fieldErrors.value = { ...fieldErrors.value, [fieldName]: error }
    return
  }

  const newErrors = { ...fieldErrors.value }
  delete newErrors[fieldName]
  fieldErrors.value = newErrors

  const value = rawValue === '' ? null : parseFloat(rawValue)
  await patch({ [fieldName]: value })

  // After a successful save, re-check the partner field to clear stale errors
  const partnerSuffix = fieldName.endsWith('_min') ? '_max' : '_min'
  const partnerField = fieldName.slice(0, -4) + partnerSuffix
  if (fieldErrors.value[partnerField]) {
    const partnerVal = preset.value?.[partnerField]
    const partnerError =
      partnerVal !== null && partnerVal !== undefined
        ? validateField(partnerField, String(partnerVal))
        : null
    if (!partnerError) {
      const cleared = { ...fieldErrors.value }
      delete cleared[partnerField]
      fieldErrors.value = cleared
    }
  }
}

function startEditName() {
  editName.value = preset.value.name
  editingName.value = true
  nextTick(() => nameInputEl.value?.focus())
}

function cancelEditName() {
  editingName.value = false
}

async function saveName() {
  const name = editName.value.trim()
  editingName.value = false
  if (!name || name === preset.value.name) return
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
    if (!res.ok) throw new Error(res.status)
    window.location.href = presetListUrl
  } catch (e) {
    saveStatus.value = 'error'
  }
}

onMounted(loadPreset)
</script>

<style scoped>
.input-wrapper {
  position: relative;
  display: inline-block;
}

.input-error {
  border-color: #dc3545 !important;
  outline-color: #dc3545;
}

.input-error:focus {
  box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.25);
}

.error-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1e1e1e;
  color: #fff;
  font-size: 0.75rem;
  line-height: 1.4;
  padding: 5px 9px;
  border-radius: 4px;
  white-space: nowrap;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
}

.error-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: #1e1e1e;
}
</style>
