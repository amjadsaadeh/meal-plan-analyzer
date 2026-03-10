<template>
  <div class="food-editor-root">
    <!-- Loading state -->
    <div v-if="!food && !loadError" class="editor-loading">
      <span class="loading-spinner"></span>
    </div>
    <div v-else-if="loadError" class="editor-error">{{ i18n.notFound }}</div>

    <template v-else>
      <!-- Header -->
      <div class="editor-header">
        <a :href="foodListUrl" class="back-link">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          {{ i18n.backToList }}
        </a>

        <div class="editor-title-row">
          <div class="title-and-badge">
            <h1
              ref="titleEl"
              class="food-name"
              :class="{ editable: isCustom, readonly: !isCustom }"
              :contenteditable="isCustom ? 'true' : 'false'"
              :placeholder="i18n.nameLabel"
              @input="onNameInput"
              @blur="onNameBlur"
              @keydown.enter.prevent="titleEl && titleEl.blur()"
            ></h1>
            <span class="source-badge" :class="isCustom ? 'source-custom' : 'source-bls'">
              {{ isCustom ? i18n.customBadge : i18n.blsBadge }}
            </span>
          </div>
          <div class="sync-status">
            <span class="sync-text">{{ syncText }}</span>
            <span class="sync-icon" v-html="syncIcon"></span>
          </div>
        </div>

        <div v-if="!isCustom" class="readonly-hint">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          {{ i18n.readonlyHint }}
        </div>
      </div>

      <!-- Nutrient groups -->
      <div class="nutrient-groups">
        <div v-for="group in nutrientGroups" :key="group.label" class="nutrient-group">
          <h2 class="group-label">{{ group.label }}</h2>
          <div class="nutrient-grid">
            <div
              v-for="field in group.fields"
              :key="field.food_key"
              class="field-row"
              :class="{ 'field-readonly': !isCustom }"
            >
              <label class="field-label">{{ field.label }}</label>
              <div class="field-input-wrap">
                <input
                  v-if="isCustom"
                  type="number"
                  step="any"
                  min="0"
                  class="field-input"
                  :value="food[field.food_key]"
                  @change="onFieldChange(field.food_key, $event.target.value)"
                />
                <span v-else class="field-value">
                  {{ formatValue(food[field.food_key], field.precision) }}
                </span>
                <span class="field-unit">{{ field.unit }}</span>
                <button
                  v-if="!isCustom"
                  class="copy-btn"
                  :class="{ copied: copyFeedback === field.food_key }"
                  :title="copyFeedback === field.food_key ? i18n.copiedToClipboard : ''"
                  @click="copyToClipboard(field.food_key, food[field.food_key])"
                >
                  <template v-if="copyFeedback === field.food_key">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  </template>
                  <template v-else>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  </template>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, watch } from 'vue'

const foodId = inject('foodId')
const csrfToken = inject('csrfToken')
const nutrients = inject('nutrients')
const i18n = inject('i18n')
const foodListUrl = inject('foodListUrl')

const food = ref(null)
const loadError = ref(false)
const syncStatus = ref('saved')   // 'saved' | 'pending' | 'error'
const syncMessage = ref('')
const copyFeedback = ref(null)
const titleEl = ref(null)

let saveTimer = null

const isCustom = computed(() => food.value?.data_source === 'custom')

const syncText = computed(() => {
  if (syncStatus.value === 'saved') return i18n.saved
  if (syncStatus.value === 'error') return syncMessage.value || i18n.error
  return i18n.saving
})

const syncIcon = computed(() => {
  if (syncStatus.value === 'saved') {
    return `<svg class="status-saved" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`
  }
  if (syncStatus.value === 'error') {
    return `<svg class="status-error" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`
  }
  return `<svg class="status-pending" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>`
})

// Group nutrients into sections
const nutrientGroups = computed(() => {
  const energyKeys = new Set(['energy_in_kcal_per_100g', 'energy_in_kj_per_100g'])
  const vitaminKeys = new Set([
    'vitc_in_mg_per_100g', 'vita_in_mug_per_100g', 'vitd_in_mug_per_100g',
    'vitb1_in_mg_per_100g', 'vitb2_in_mg_per_100g', 'vitb3_in_mg_per_100g',
    'vitb5_in_mg_per_100g', 'vitb6_in_mug_per_100g', 'vitb12_in_mug_per_100g',
    'biotin_in_mug_per_100g',
  ])
  const mineralKeys = new Set([
    'iron_in_mg_per_100g', 'magnesium_in_mg_per_100g', 'zinc_in_mg_per_100g',
    'calcium_in_mg_per_100g', 'iodine_in_mug_per_100g', 'copper_in_mug_per_100g',
    'manganese_in_mug_per_100g', 'molybdenum_in_mug_per_100g',
  ])

  const energy = [], macros = [], vitamins = [], minerals = []

  // Add energy_in_kj first (not in nutrients array from NUTRIENTS dict)
  energy.push({ food_key: 'energy_in_kcal_per_100g', label: i18n.energyKcal || 'Energy (kcal)', unit: 'kcal', precision: 1 })
  energy.push({ food_key: 'energy_in_kj_per_100g', label: i18n.energyKj || 'Energy (kJ)', unit: 'kJ', precision: 1 })

  for (const n of nutrients) {
    if (energyKeys.has(n.food_key)) continue  // already added above
    if (vitaminKeys.has(n.food_key)) vitamins.push(n)
    else if (mineralKeys.has(n.food_key)) minerals.push(n)
    else macros.push(n)
  }

  return [
    { label: i18n.energy || 'Energy', fields: energy },
    { label: i18n.macronutrients || 'Macronutrients', fields: macros },
    { label: i18n.vitamins || 'Vitamins', fields: vitamins },
    { label: i18n.minerals || 'Minerals', fields: minerals },
  ].filter(g => g.fields.length > 0)
})

async function loadFood() {
  try {
    const res = await fetch(`/api/foods/${foodId}/`)
    if (!res.ok) { loadError.value = true; return }
    food.value = await res.json()
    if (titleEl.value) titleEl.value.textContent = food.value.name
  } catch {
    loadError.value = true
  }
}

async function apiPatch(body) {
  syncStatus.value = 'pending'
  try {
    const res = await fetch(`/api/foods/${foodId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body),
    })
    if (res.ok) {
      const updated = await res.json()
      // update local food with server response
      Object.assign(food.value, updated)
      syncStatus.value = 'saved'
    } else {
      const err = await res.json().catch(() => ({}))
      syncMessage.value = err.detail || i18n.error
      syncStatus.value = 'error'
    }
  } catch {
    syncMessage.value = i18n.networkError
    syncStatus.value = 'error'
  }
}

function scheduleSave(patch) {
  syncStatus.value = 'pending'
  clearTimeout(saveTimer)
  saveTimer = setTimeout(() => apiPatch(patch), 800)
}

function onFieldChange(foodKey, rawValue) {
  const value = parseFloat(rawValue)
  if (isNaN(value)) return
  food.value[foodKey] = value

  const patch = { [foodKey]: value }

  // Sync energy fields locally
  if (foodKey === 'energy_in_kcal_per_100g') {
    const kj = value * 4.184
    food.value.energy_in_kj_per_100g = Math.round(kj * 10) / 10
  } else if (foodKey === 'energy_in_kj_per_100g') {
    const kcal = value / 4.184
    food.value.energy_in_kcal_per_100g = Math.round(kcal * 10) / 10
  }

  scheduleSave(patch)
}

function onNameInput(e) {
  const name = e.target.textContent.trim()
  if (food.value) food.value.name = name
  scheduleSave({ name })
}

function onNameBlur(e) {
  const name = e.target.textContent.trim()
  if (!name && food.value) {
    e.target.textContent = food.value.name
  }
}

function copyToClipboard(fieldKey, value) {
  navigator.clipboard.writeText(String(value ?? '')).catch(() => {})
  copyFeedback.value = fieldKey
  setTimeout(() => { copyFeedback.value = null }, 1500)
}

function formatValue(val, precision) {
  if (val == null) return '—'
  return Number(val).toFixed(precision ?? 1)
}

onMounted(async () => {
  await loadFood()
  if (titleEl.value && food.value) {
    titleEl.value.textContent = food.value.name
  }
})

// Keep title element in sync if food loads after mount
watch(() => food.value?.name, (name) => {
  if (titleEl.value && name && titleEl.value.textContent !== name) {
    titleEl.value.textContent = name
  }
})
</script>
