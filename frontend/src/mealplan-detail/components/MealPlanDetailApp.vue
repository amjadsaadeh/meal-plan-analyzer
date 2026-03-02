<template>
  <!-- Global food search dropdown -->
  <FoodSearchDropdown
    :visible="search.visible"
    :position="search.position"
    :results="search.results"
    :query="search.query"
    @select="onFoodSelect"
  />

  <!-- Delete ingredient modal -->
  <ConfirmDeleteIngredientModal
    :open="deleteFoodModal.open"
    :ingredient-name="deleteFoodModal.row?.food_data?.name || deleteFoodModal.row?.food?.name || ''"
    @confirm="confirmDeleteFood"
    @cancel="deleteFoodModal.open = false"
  />

  <!-- Save preset modal -->
  <SavePresetModal
    :open="presetModal.open"
    :thresholds="plan ? plan.thresholds : {}"
    :nutrients="nutrients"
    @confirm="confirmSavePreset"
    @cancel="presetModal.open = false"
  />

  <!-- Sticky bar — always rendered so CSS transition works -->
  <StickyBar
    :class="{ visible: stickyVisible }"
    :plan-name="plan ? plan.name : ''"
    :sync-status="syncStatus"
    :sync-message="syncMessage"
    :visible-nutrients="visibleNutrients"
    :nutrients="nutrients"
    @toggle-columns="openColDropdown"
  />

  <!-- Column visibility dropdown -->
  <Teleport to="body">
    <div
      v-if="colDropdown.open"
      id="colDropdown"
      class="col-dropdown active"
      :style="{ 
        top: colDropdown.top + 'px', 
        left: colDropdown.left + 'px', 
        maxHeight: 'calc(100vh - ' + (colDropdown.top + 20) + 'px)',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        boxSizing: 'border-box'
      }"
      @click.stop
    >
      <label
        v-for="nut in nonEnergyNutrients"
        :key="nut.key"
        class="col-option"
      >
        <input
          type="checkbox"
          :data-col="nut.key"
          :checked="visibleNutrients.includes(nut.key)"
          @change="toggleCol(nut.key, $event.target.checked)"
        >
        {{ nut.label }}
      </label>
    </div>
  </Teleport>

  <div class="container" v-if="plan">
    <!-- Scroll sentinel: when this element leaves viewport, sticky bar appears -->
    <div ref="sentinelRef" style="position: absolute; top: 0; height: 1px; pointer-events: none;"></div>

    <a :href="planListUrl" class="btn-back">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;">
        <line x1="19" y1="12" x2="5" y2="12"></line>
        <polyline points="12 19 5 12 12 5"></polyline>
      </svg>
      {{ i18n.backToPlans }}
    </a>

    <PageHeader
      :plan="plan"
      :sync-status="syncStatus"
      :sync-message="syncMessage"
      :pdf-url="pdfUrl"
      :preview-url="previewUrl"
      @update:name="onPlanNameChange"
    />

    <Toolbar
      :nutrients="nutrients"
      :visible-nutrients="visibleNutrients"
      @add-day="addDay"
      @open-col-dropdown="openColDropdown"
      @apply-preset="applyPreset"
    />

    <div class="meal-sections-container">
      <DaySection
        v-for="day in days"
        :key="day.id"
        :day="day"
        :nutrients="nutrients"
        :visible-nutrients="visibleNutrients"
        :thresholds="plan.thresholds"
        @update:name="onDayNameChange(day.id, $event)"
        @delete="openDeleteDayModal(day)"
        @request-delete="openDeleteFoodModal"
        @food-saved="onFoodSaved(day.id, $event)"
        @food-deleted="onFoodDeleted(day.id, $event)"
        @open-save-preset="presetModal.open = true"
        @update-threshold="onUpdateThreshold"
        @activate-search="activateSearch"
        @deactivate-search="closeSearch"
      />
    </div>

    <PlanOverview
      :days="days"
      :nutrients="nutrients"
      :visible-nutrients="visibleNutrients"
      :thresholds="plan.thresholds"
      @open-save-preset="presetModal.open = true"
      @update-threshold="onUpdateThreshold"
    />
  </div>

  <div v-else class="container">
    <p style="color: var(--text-dim); padding: 2rem 0;">Loading...</p>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, inject, provide, watch, nextTick } from 'vue'
import FoodSearchDropdown from './FoodSearchDropdown.vue'
import ConfirmDeleteDayModal from './ConfirmDeleteDayModal.vue'
import ConfirmDeleteIngredientModal from './ConfirmDeleteIngredientModal.vue'
import SavePresetModal from './SavePresetModal.vue'
import StickyBar from './StickyBar.vue'
import PageHeader from './PageHeader.vue'
import Toolbar from './Toolbar.vue'
import DaySection from './DaySection.vue'
import PlanOverview from './PlanOverview.vue'



const planId = inject('planId')
const csrfToken = inject('csrfToken')
const nutrients = inject('nutrients')
const i18n = inject('i18n')
const pdfUrl = inject('pdfUrl')
const previewUrl = inject('previewUrl')
const planListUrl = inject('planListUrl')

// ── State ──────────────────────────────────────────────────────────────────
const plan = ref(null)
const days = ref([])
const syncStatus = ref('saved')
const syncMessage = ref('')
const stickyVisible = ref(false)
const sentinelRef = ref(null)

const colDropdown = reactive({ open: false, top: 0, left: 0 })
const deleteModal = reactive({ open: false, dayId: null, dayName: '' })
const deleteFoodModal = reactive({ open: false, row: null })
const presetModal = reactive({ open: false })

const search = reactive({
  visible: false,
  position: { top: 0, left: 0, width: 320 },
  results: [],
  query: '',
  onSelect: null,
})

// ── Computed ───────────────────────────────────────────────────────────────
const nonEnergyNutrients = computed(() => nutrients.filter(n => n.key !== 'energy_in_kcal'))

const visibleNutrients = computed(() => {
  if (!plan.value || !plan.value.visible_nutrients || plan.value.visible_nutrients.length === 0) {
    return nonEnergyNutrients.value.map(n => n.key)
  }
  return plan.value.visible_nutrients
})

// ── Provide food search to children ───────────────────────────────────────
let searchTimer = null

provide('doFoodSearch', async (query, inputEl) => {
  search.query = query
  if (inputEl) {
    const rect = inputEl.getBoundingClientRect()
    search.position = {
      top: rect.bottom + 5,
      left: rect.left,
      width: Math.max(rect.width, 320),
    }
  }
  if (query.length < 2) {
    search.visible = false
    search.results = []
    return
  }
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    try {
      const res = await fetch(`/api/foods/?search=${encodeURIComponent(query)}`)
      const data = await res.json()
      search.results = data
      search.visible = true
    } catch (e) {
      console.error(e)
    }
  }, 300)
})

// ── API ────────────────────────────────────────────────────────────────────
let planNameTimer = null
let thresholdTimer = null

function setSyncStatus(status, message = '') {
  syncStatus.value = status
  syncMessage.value = message
}

async function apiPatch(url, body) {
  setSyncStatus('pending')
  try {
    const res = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body),
    })
    if (res.ok) {
      setSyncStatus('saved')
      return await res.json()
    }
    setSyncStatus('error', 'Error: ' + res.status)
    return null
  } catch (e) {
    setSyncStatus('error', i18n.networkError)
    return null
  }
}

// ── Data loading ───────────────────────────────────────────────────────────
async function loadPlan() {
  try {
    const res = await fetch(`/api/mealplans/${planId}/`)
    if (!res.ok) return
    const data = await res.json()
    plan.value = data
    days.value = (data.days || []).filter(d => !d.removed)
  } catch (e) {
    console.error('Failed to load plan:', e)
  }
}

// ── Plan name ──────────────────────────────────────────────────────────────
function onPlanNameChange(name) {
  plan.value.name = name
  setSyncStatus('pending')
  clearTimeout(planNameTimer)
  planNameTimer = setTimeout(() => apiPatch(`/api/mealplans/${planId}/`, { name }), 800)
}

// ── Day name ───────────────────────────────────────────────────────────────
async function onDayNameChange(dayId, name) {
  const day = days.value.find(d => d.id === dayId)
  if (day) day.name = name
  await apiPatch(`/api/mealplan-days/${dayId}/`, { name })
}

// ── Add day ────────────────────────────────────────────────────────────────
async function addDay() {
  const nextNum = days.value.length + 1
  setSyncStatus('pending')
  try {
    const res = await fetch('/api/mealplan-days/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ meal_plan: parseInt(planId), name: `${i18n.dayPrefix} ${nextNum}` }),
    })
    if (res.ok) {
      const newDay = await res.json()
      newDay.foods = []
      days.value.push(newDay)
      setSyncStatus('saved')
    } else {
      setSyncStatus('error', i18n.errorCreatingDay)
    }
  } catch (e) {
    setSyncStatus('error', i18n.networkError)
  }
}

// ── Delete day ─────────────────────────────────────────────────────────────
function openDeleteDayModal(day) {
  deleteModal.dayId = day.id
  deleteModal.dayName = day.name
  deleteModal.open = true
}

async function confirmDeleteDay() {
  deleteModal.open = false
  const dayId = deleteModal.dayId
  setSyncStatus('pending', i18n.deleting)
  try {
    const res = await fetch(`/api/mealplan-days/${dayId}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ removed: true }),
    })
    if (res.ok) {
      days.value = days.value.filter(d => d.id !== dayId)
      setSyncStatus('saved')
    } else {
      setSyncStatus('error', 'Delete Error')
    }
  } catch (e) {
    setSyncStatus('error', i18n.networkError)
  }
}

// ── Delete food ───────────────────────────────────────────────────────────
function openDeleteFoodModal(row) {
  deleteFoodModal.row = row
  deleteFoodModal.open = true
}

async function confirmDeleteFood() {
  const row = deleteFoodModal.row
  if (!row) return
  deleteFoodModal.open = false
  setSyncStatus('pending', i18n.deleting)

  try {
    const res = await fetch(`/api/mealplan-foods/${row.id}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': csrfToken },
    })
    if (res.ok) {
      // Find the day this food belongs to. 
      // Row might not have dayId directly if it's from MealSection props.
      // But we can search through our days state.
      for (const day of days.value) {
        if (day.foods.some(f => f.id === row.id)) {
          onFoodDeleted(day.id, row.id)
          break
        }
      }
      setSyncStatus('saved')
    } else {
      setSyncStatus('error', i18n.errorDeletingRow)
    }
  } catch (e) {
    console.error(e)
    setSyncStatus('error', i18n.networkError)
  }
}

// ── Food saved/deleted ─────────────────────────────────────────────────────
function onFoodSaved(dayId, mpf) {
  const day = days.value.find(d => d.id === dayId)
  if (!day) return
  const idx = day.foods.findIndex(f => f.id === mpf.id)
  if (idx !== -1) day.foods[idx] = mpf
  else day.foods.push(mpf)
}

function onFoodDeleted(dayId, mpfId) {
  const day = days.value.find(d => d.id === dayId)
  if (!day) return
  day.foods = day.foods.filter(f => f.id !== mpfId)
}

// ── Thresholds ─────────────────────────────────────────────────────────────
function onUpdateThreshold(nutKey, type, value) {
  if (!plan.value.thresholds) plan.value.thresholds = {}
  if (!plan.value.thresholds[nutKey]) plan.value.thresholds[nutKey] = {}
  plan.value.thresholds[nutKey][type] = value === '' ? null : (parseFloat(value) || null)
  clearTimeout(thresholdTimer)
  setSyncStatus('pending')
  thresholdTimer = setTimeout(() => apiPatch(`/api/mealplans/${planId}/`, { thresholds: plan.value.thresholds }), 800)
}

// ── Column visibility ──────────────────────────────────────────────────────
function toggleCol(nutKey, show) {
  const current = plan.value.visible_nutrients || []
  plan.value.visible_nutrients = show
    ? [...current.filter(k => k !== nutKey), nutKey]
    : current.filter(k => k !== nutKey)
  apiPatch(`/api/mealplans/${planId}/`, { visible_nutrients: plan.value.visible_nutrients })
}

function openColDropdown(btnEl) {
  if (colDropdown.open) { colDropdown.open = false; return }
  const rect = btnEl.getBoundingClientRect()
  colDropdown.top = rect.bottom + 8
  colDropdown.left = rect.right - 200
  colDropdown.open = true
}

// ── Presets ────────────────────────────────────────────────────────────────
async function applyPreset(preset) {
  if (!confirm(`${preset.name}: ${i18n.confirmApplyTemplate}`)) return
  const newThresholds = {}
  nutrients.forEach(n => {
    newThresholds[n.key] = {
      min: preset[`${n.key}_min`] ?? null,
      max: preset[`${n.key}_max`] ?? null,
    }
  })
  plan.value.thresholds = newThresholds
  await apiPatch(`/api/mealplans/${planId}/`, { thresholds: newThresholds })
}

async function confirmSavePreset(name) {
  const body = { name }
  nutrients.forEach(n => {
    const t = plan.value.thresholds?.[n.key] || {}
    body[`${n.key}_min`] = t.min ?? null
    body[`${n.key}_max`] = t.max ?? null
  })
  try {
    const res = await fetch('/api/threshold-presets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body),
    })
    if (res.ok) {
      presetModal.open = false
      alert(`"${name}": ${i18n.templateSavedSuccess}`)
    } else {
      const err = await res.json()
      alert(err.name ? err.name[0] : i18n.savingError)
    }
  } catch (e) {
    alert(i18n.networkError)
  }
}

// ── Food search ────────────────────────────────────────────────────────────
function activateSearch(cellEl, onSelect) {
  search.onSelect = onSelect
  if (cellEl) {
    const rect = cellEl.getBoundingClientRect()
    search.position = {
      top: rect.bottom + 5,
      left: rect.left,
      width: Math.max(rect.width, 320),
    }
  }
  search.visible = false
  search.results = []
  search.query = ''
}

function closeSearch() {
  search.visible = false
  search.results = []
  search.onSelect = null
  search.query = ''
}

function onFoodSelect(food) {
  if (search.onSelect) search.onSelect(food)
  closeSearch()
}

// ── Global click handler ───────────────────────────────────────────────────
function onDocumentClick(e) {
  if (!e.target.closest?.('.col-dropdown') && colDropdown.open) {
    colDropdown.open = false
  }
  if (!e.target.closest?.('.search-dropdown') && !e.target.closest?.('.ingredient-name-cell')) {
    closeSearch()
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
let observer = null

onMounted(async () => {
  await loadPlan()
  document.addEventListener('click', onDocumentClick)

  // Set up IntersectionObserver after plan loads and sentinel renders
  await nextTick()
  if (sentinelRef.value) {
    observer = new IntersectionObserver(([entry]) => {
      stickyVisible.value = !entry.isIntersecting
    }, { threshold: 0 })
    observer.observe(sentinelRef.value)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
  if (observer) observer.disconnect()
})
</script>
