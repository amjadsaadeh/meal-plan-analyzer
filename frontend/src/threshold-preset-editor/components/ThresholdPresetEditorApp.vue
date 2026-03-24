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
            v-for="nutrient in defaultNutrients"
            :key="nutrient.key"
            class="nutrient-row"
          >
            <span class="nutrient-label">
              {{ nutrient.label }}
              <span class="nutrient-unit">({{ nutrient.unit }})</span>
            </span>
            <div class="nutrient-inputs">
              <span class="input-label">{{ i18n.min }}</span>
              <input
                class="nutrient-min-input threshold-input"
                type="number"
                step="any"
                :value="preset[nutrient.key + '_min'] ?? ''"
                @blur="saveField(nutrient.key + '_min', $event.target.value)"
                :placeholder="i18n.min"
              />
              <span class="input-label">{{ i18n.max }}</span>
              <input
                class="nutrient-max-input threshold-input"
                type="number"
                step="any"
                :value="preset[nutrient.key + '_max'] ?? ''"
                @blur="saveField(nutrient.key + '_max', $event.target.value)"
                :placeholder="i18n.max"
              />
            </div>
          </div>
        </div>

        <!-- Expand toggle -->
        <button class="btn-expand-chevron expand-toggle" @click="expanded = !expanded">
          <svg
            width="16" height="16" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round"
            :style="{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
          {{ expanded ? i18n.showLess : i18n.showMore }}
        </button>

        <!-- Expanded nutrients -->
        <div class="expanded-content" :class="{ open: expanded }">
          <div class="editor-expanded-inner expanded-inner">
            <div
              v-for="nutrient in extendedNutrients"
              :key="nutrient.key"
              class="nutrient-row"
              style="border-top: 1px solid var(--glass-border);"
            >
              <span class="nutrient-label">
                {{ nutrient.label }}
                <span class="nutrient-unit">({{ nutrient.unit }})</span>
              </span>
              <div class="nutrient-inputs">
                <span class="input-label">{{ i18n.min }}</span>
                <input
                  class="nutrient-min-input threshold-input"
                  type="number"
                  step="any"
                  :value="preset[nutrient.key + '_min'] ?? ''"
                  @blur="saveField(nutrient.key + '_min', $event.target.value)"
                  :placeholder="i18n.min"
                />
                <span class="input-label">{{ i18n.max }}</span>
                <input
                  class="nutrient-max-input threshold-input"
                  type="number"
                  step="any"
                  :value="preset[nutrient.key + '_max'] ?? ''"
                  @blur="saveField(nutrient.key + '_max', $event.target.value)"
                  :placeholder="i18n.max"
                />
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
import { ref, computed, inject, onMounted, nextTick } from 'vue'

const presetId = inject('presetId')
const csrfToken = inject('csrfToken')
const nutrients = inject('nutrients')
const i18n = inject('i18n')
const presetListUrl = inject('presetListUrl')

const DEFAULT_KEYS = [
  'energy_in_kcal',
  'water_in_g',
  'carbohydrate_in_g',
  'fat_in_g',
  'protein_in_g',
]

const preset = ref(null)
const notFound = ref(false)
const saveStatus = ref('idle')
const editingName = ref(false)
const editName = ref('')
const nameInputEl = ref(null)
const expanded = ref(false)

const defaultNutrients = computed(() =>
  nutrients.filter((n) => DEFAULT_KEYS.includes(n.key))
)
const extendedNutrients = computed(() =>
  nutrients.filter((n) => !DEFAULT_KEYS.includes(n.key))
)

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
    preset.value = await res.json()
    saveStatus.value = 'saved'
    setTimeout(() => {
      if (saveStatus.value === 'saved') saveStatus.value = 'idle'
    }, 2000)
  } catch (e) {
    saveStatus.value = 'error'
  }
}

async function saveField(fieldName, rawValue) {
  const value = rawValue === '' ? null : parseFloat(rawValue)
  await patch({ [fieldName]: value })
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
