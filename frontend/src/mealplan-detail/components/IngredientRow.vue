<template>
  <tr
    class="ingredient-row"
    :data-id="row.id || ''"
    :data-food-id="row.food?.id || ''"
  >
    <!-- Ingredient / Search cell -->
    <td>
      <div
        class="cell-content editable-cell ingredient-name-cell"
        tabindex="0"
        @click="onCellClick"
        @focus="onCellClick"
      >
        <template v-if="!isSearching">
          <span>{{ row.food ? row.food.name : i18n.searchFood }}</span>
          <span v-if="row.food" class="bls-code">{{ row.food.bls_code }}</span>
        </template>
        <input
          v-else
          ref="searchInputEl"
          type="text"
          class="table-input"
          :placeholder="i18n.searchFood"
          :value="searchQuery"
          autocomplete="off"
          @input="onSearchInput"
          @keydown.esc="cancelSearch"
          @blur="onSearchBlur"
        >
      </div>
    </td>

    <!-- Amount -->
    <td>
      <input
        type="number"
        class="table-input amount-input"
        :class="{ 'amount-zero': localAmount !== '' && parseFloat(localAmount) === 0 }"
        :value="localAmount"
        @input="onAmountInput"
        @blur="onAmountBlur"
        @keydown.enter.prevent="onAmountEnter"
        @keydown.esc.prevent="$event.target.blur()"
        :placeholder="row._isDraft ? '0.0' : ''"
      >
    </td>

    <!-- Energy (kcal) — always visible -->
    <td>
      <div class="cell-content energy_in_kcal-cell">{{ nutVal('energy_in_kcal', 1) }}</div>
    </td>

    <!-- Other nutrients -->
    <td
      v-for="nut in nonEnergyNutrients"
      :key="nut.key"
      :class="['col-' + nut.key, { 'hidden-col': !visibleNutrients.includes(nut.key) }]"
    >
      <div class="cell-content" :class="nut.key + '-cell'">{{ nutVal(nut.key, nut.precision) }}</div>
    </td>

    <!-- Delete -->
    <td class="actions-cell">
      <button class="delete-btn" @click="$emit('delete')" v-if="!row._isDraft || row.food">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          <line x1="10" y1="11" x2="10" y2="17"></line>
          <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
      </button>
    </td>
  </tr>
</template>

<script setup>
import { ref, computed, watch, nextTick, inject } from 'vue'

const i18n = inject('i18n')
const doFoodSearch = inject('doFoodSearch')
const searchCtx = inject('search')

const props = defineProps({
  row: { type: Object, required: true },
  nutrients: { type: Array, default: () => [] },
  visibleNutrients: { type: Array, default: () => [] },
  dayId: { type: Number, required: true },
  mealType: { type: String, required: true },
})

const emit = defineEmits(['save', 'delete', 'activate-search', 'deactivate-search'])

const isSearching = ref(false)
const searchQuery = ref('')
const searchInputEl = ref(null)

// Local amount mirrors the row amount; allows editing without immediately mutating the prop
const localAmount = ref(props.row.amount_in_g !== null && props.row.amount_in_g !== undefined ? String(props.row.amount_in_g) : '')

watch(() => props.row.amount_in_g, (val) => {
  if (val !== null && val !== undefined) localAmount.value = String(val)
})

// Local food: starts from row.food_data or row.food (search result)
const localFood = ref(props.row.food_data || props.row.food || null)

watch(() => props.row.food_data, (val) => { if (val) localFood.value = val })

const nonEnergyNutrients = computed(() => props.nutrients.filter(n => n.key !== 'energy_in_kcal'))

function nutVal(nutKey, precision) {
  const food = localFood.value
  if (!food) return (0).toFixed(precision ?? 1)
  const nut = props.nutrients.find(n => n.key === nutKey)
  if (!nut) return (0).toFixed(precision ?? 1)
  const amount = parseFloat(localAmount.value) || 0
  return ((food[nut.food_key] || 0) * amount / 100).toFixed(precision ?? 1)
}

// ── Search ──────────────────────────────────────────────────────────────────
async function onCellClick() {
  if (isSearching.value) return
  isSearching.value = true
  searchQuery.value = localFood.value ? localFood.value.name : ''

  await nextTick()
  if (searchInputEl.value) {
    searchInputEl.value.focus()
    if (searchQuery.value) searchInputEl.value.select()
  }

  // Activate the global search
  emit('activate-search', {
    el: searchInputEl.value,
    cb: onFoodSelected,
  })

  if (searchQuery.value.length >= 2) {
    doFoodSearch(searchQuery.value, searchInputEl.value)
  }
}

function onSearchInput(e) {
  searchQuery.value = e.target.value
  doFoodSearch(searchQuery.value, e.target)
}

function onFoodSelected(food) {
  localFood.value = food
  isSearching.value = false
  searchQuery.value = ''
  // Trigger save once amount is known (or if already set)
  if (localAmount.value !== '') {
    emitSave()
  }
  // Focus the amount input
  nextTick(() => {
    const amountEl = searchInputEl.value?.closest('tr')?.querySelector('.amount-input')
    if (amountEl) { amountEl.focus(); amountEl.select() }
  })
}

function cancelSearch() {
  isSearching.value = false
  searchQuery.value = ''
  emit('deactivate-search')
}

function onSearchBlur() {
  // Small delay so mousedown on dropdown item can fire first
  setTimeout(() => {
    if (isSearching.value) {
      isSearching.value = false
      searchQuery.value = ''
    }
  }, 200)
}

// ── Amount ──────────────────────────────────────────────────────────────────
function onAmountInput(e) {
  localAmount.value = e.target.value
}

function onAmountBlur() {
  if (localFood.value && localAmount.value !== '') {
    emitSave()
  }
}

function onAmountEnter(e) {
  e.target.blur()
}

function emitSave() {
  emit('save', {
    food: localFood.value,
    amount_in_g: localAmount.value,
    existingId: props.row._isDraft ? null : props.row.id,
  })
}
</script>
