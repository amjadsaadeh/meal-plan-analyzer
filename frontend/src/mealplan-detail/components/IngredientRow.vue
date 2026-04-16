<template>
  <tr
    class="ingredient-row"
    :data-id="row._isDraft ? null : row.id"
    :data-food-id="row._isDraft ? null : (localFood ? localFood.id : null)"
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
          <span>{{ localFood ? localFood.name : i18n.searchFood }}</span>
          <span v-if="localFood" class="bls-code">{{ localFood.bls_code }}</span>
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
        @keydown.esc.prevent="($event.target as HTMLInputElement).blur()"
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
      <button class="delete-btn" @click="$emit('delete')" v-if="!row._isDraft || localFood">
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

<script setup lang="ts">
import { ref, computed, watch, nextTick, inject } from 'vue'
import type { I18n, Nutrient, Food, MealPlanFood, ActivateSearchPayload } from '../../types/index'

const i18n = inject<I18n>('i18n')!
const doFoodSearch = inject<(query: string, inputEl: HTMLElement | null) => void>('doFoodSearch')!

type RowProp = (MealPlanFood & { _isDraft?: boolean }) | { _isDraft: true; id: null; food: null; amount_in_g: string; food_data?: undefined }

const props = withDefaults(defineProps<{
  row: RowProp
  nutrients?: Nutrient[]
  visibleNutrients?: string[]
  dayId: number
  mealType: string
}>(), {
  nutrients: () => [],
  visibleNutrients: () => [],
})

const emit = defineEmits<{
  'save': [payload: { food: Food; amount_in_g: string; existingId: number | null }]
  'delete': []
  'activate-search': [payload: ActivateSearchPayload]
  'deactivate-search': []
}>()

const isSearching = ref(false)
const searchQuery = ref('')
const searchInputEl = ref<HTMLInputElement | null>(null)

const localAmount = ref(
  props.row.amount_in_g !== null && props.row.amount_in_g !== undefined
    ? String(props.row.amount_in_g)
    : ''
)

watch(() => props.row.amount_in_g, (val) => {
  if (val !== null && val !== undefined) localAmount.value = String(val)
})

const localFood = ref<Food | null>(props.row.food_data ?? null)

watch(() => props.row.food_data, (val) => { if (val) localFood.value = val })

const nonEnergyNutrients = computed(() => props.nutrients.filter(n => n.key !== 'energy_in_kcal'))

function nutVal(nutKey: string, precision: number): string {
  const food = localFood.value
  if (!food) return (0).toFixed(precision ?? 1)
  const nut = props.nutrients.find(n => n.key === nutKey)
  if (!nut) return (0).toFixed(precision ?? 1)
  const amount = parseFloat(localAmount.value) || 0
  return (((food[nut.food_key] as number) || 0) * amount / 100).toFixed(precision ?? 1)
}

async function onCellClick() {
  if (isSearching.value) return
  isSearching.value = true
  searchQuery.value = localFood.value ? localFood.value.name : ''

  await nextTick()
  if (searchInputEl.value) {
    searchInputEl.value.focus()
    if (searchQuery.value) searchInputEl.value.select()
  }

  emit('activate-search', {
    el: searchInputEl.value!,
    cb: onFoodSelected,
  })

  if (searchQuery.value.length >= 2) {
    doFoodSearch(searchQuery.value, searchInputEl.value)
  }
}

function onSearchInput(e: Event) {
  const target = e.target as HTMLInputElement
  searchQuery.value = target.value
  doFoodSearch(searchQuery.value, target)
}

function onFoodSelected(food: Food) {
  localFood.value = food
  isSearching.value = false
  searchQuery.value = ''
  if (localAmount.value !== '') {
    emitSave()
  }
  nextTick(() => {
    const amountEl = searchInputEl.value?.closest('tr')?.querySelector<HTMLInputElement>('.amount-input')
    if (amountEl) { amountEl.focus(); amountEl.select() }
  })
}

function cancelSearch() {
  isSearching.value = false
  searchQuery.value = ''
  emit('deactivate-search')
}

function onSearchBlur() {
  setTimeout(() => {
    if (isSearching.value) {
      isSearching.value = false
      searchQuery.value = ''
    }
  }, 200)
}

function onAmountInput(e: Event) {
  localAmount.value = (e.target as HTMLInputElement).value
}

function onAmountBlur() {
  if (localFood.value && localAmount.value !== '') {
    emitSave()
  }
}

function onAmountEnter(e: Event) {
  (e.target as HTMLInputElement).blur()
}

function emitSave() {
  emit('save', {
    food: localFood.value!,
    amount_in_g: localAmount.value,
    existingId: props.row._isDraft ? null : (props.row as MealPlanFood).id,
  })
}
</script>
