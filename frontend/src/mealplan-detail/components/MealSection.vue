<template>
  <div class="meal-section">
    <h3 class="meal-header" style="font-size: 1.4rem; color: var(--text-dim);">
      <!-- Breakfast icon -->
      <svg v-if="mealType === 'breakfast'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 11h.01"></path><path d="M11 11h.01"></path><path d="M7 11h.01"></path>
        <path d="M12 2A10 10 0 0 1 22 12c0 1.25-.23 2.44-.65 3.54a5 5 0 0 1-7.81 0A10 10 0 0 1 3.12 11.23a5 5 0 0 1 1-6.11A10 10 0 0 1 12 2z"></path>
      </svg>
      <!-- Lunch icon -->
      <svg v-else-if="mealType === 'lunch'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle><path d="M12 6v6l4 2"></path>
      </svg>
      <!-- Dinner icon -->
      <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"></path>
      </svg>
      {{ mealLabel }}
    </h3>

    <div class="table-card">
      <div class="table-responsive">
        <table :data-meal-type="mealType" :style="{ minWidth: tableMinWidth + 'px' }">
          <thead>
            <tr>
              <th style="width: 200px;">{{ i18n.ingredient }}</th>
              <th style="width: 50px;" class="actions-cell"></th>
              <th style="width: 80px;">{{ i18n.amountG }}</th>
              <th style="width: 65px;" class="nutrient-header">kcal</th>
              <th
                v-for="nut in nonEnergyNutrients"
                :key="nut.key"
                style="width: 65px;"
                class="nutrient-header"
                :class="['col-' + nut.key, { 'hidden-col': !visibleNutrients.includes(nut.key) }]"
              >
                {{ nut.label }} ({{ nut.unit }})
              </th>
              <th style="width: 50px;" class="actions-cell"></th>
            </tr>
          </thead>
          <tbody :id="`ingredientsBody-${dayId}-${mealType}`">
            <IngredientRow
              v-for="row in allRows"
              :key="row._uid"
              :row="row"
              :nutrients="nutrients"
              :visible-nutrients="visibleNutrients"
              :day-id="dayId"
              :meal-type="mealType"
              @save="onSaveRow"
              @delete="onDeleteRow(row)"
              @activate-search="onActivateSearch"
              @deactivate-search="$emit('deactivate-search')"
            />
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" style="text-align: right; padding-right: 1.5rem; color: var(--text-dim); text-transform: uppercase; font-size: 0.7rem;">{{ i18n.subtotal }}</td>
              <td><div class="cell-content total-value">{{ fmt(mealTotals['energy_in_kcal'], 1) }}</div></td>
              <td
                v-for="nut in nonEnergyNutrients"
                :key="nut.key"
                :class="['col-' + nut.key, { 'hidden-col': !visibleNutrients.includes(nut.key) }]"
              >
                <div class="cell-content total-value">{{ fmt(mealTotals[nut.key], nut.precision) }}</div>
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import IngredientRow from './IngredientRow.vue'
import type { I18n, Nutrient, MealPlanFood, Food, ActivateSearchPayload } from '../../types/index'

const i18n = inject<I18n>('i18n')!
const csrfToken = inject<string>('csrfToken')!

const props = withDefaults(defineProps<{
  dayId: number
  mealType: string
  foods?: MealPlanFood[]
  nutrients?: Nutrient[]
  visibleNutrients?: string[]
}>(), {
  foods: () => [],
  nutrients: () => [],
  visibleNutrients: () => [],
})

const emit = defineEmits<{
  'food-saved': [mpf: MealPlanFood]
  'food-deleted': [mpfId: number]
  'activate-search': [payload: ActivateSearchPayload]
  'deactivate-search': []
  'request-delete': [row: MealPlanFood]
}>()

let uidCounter = 0
function makeUid() { return ++uidCounter }

type DraftRow = { _uid: number; _isDraft: true; id: null; food: null; amount_in_g: string }
type DisplayRow = (MealPlanFood & { _uid: number; _isDraft: false }) | DraftRow

const draftRow = ref<DraftRow>({ _uid: makeUid(), _isDraft: true, id: null, food: null, amount_in_g: '' })

const allRows = computed<DisplayRow[]>(() => {
  const saved: DisplayRow[] = props.foods.map(f => ({ ...f, _uid: f.id, _isDraft: false as const }))
  return [...saved, draftRow.value]
})

const nonEnergyNutrients = computed(() => props.nutrients.filter(n => n.key !== 'energy_in_kcal'))

const tableMinWidth = computed(() => {
  const visCount = nonEnergyNutrients.value.filter(n => props.visibleNutrients.includes(n.key)).length
  return 200 + 80 + 65 + (visCount * 65) + 50
})

const mealLabel = computed(() => i18n[props.mealType] || props.mealType)

const mealTotals = computed<Record<string, number>>(() => {
  const totals: Record<string, number> = {}
  props.nutrients.forEach(n => { totals[n.key] = 0 })
  props.foods.forEach(f => {
    if (!f.food_data) return
    const factor = (f.amount_in_g || 0) / 100
    props.nutrients.forEach(n => {
      totals[n.key] += ((f.food_data![n.food_key] as number) || 0) * factor
    })
  })
  return totals
})

function fmt(val: number, precision: number): string {
  return (val || 0).toFixed(precision ?? 1)
}

interface SaveRowData {
  food: Food
  amount_in_g: string
  existingId: number | null
}

async function onSaveRow(rowData: SaveRowData) {
  const { food, amount_in_g, existingId } = rowData
  if (!food || amount_in_g === '' || amount_in_g === null || parseFloat(amount_in_g) < 0) return

  const body = {
    meal_plan_day: props.dayId,
    food: food.id,
    amount_in_g: parseFloat(amount_in_g),
    meal_type: props.mealType,
  }

  const method = existingId ? 'PATCH' : 'POST'
  const url = existingId ? `/api/mealplan-foods/${existingId}/` : '/api/mealplan-foods/'

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body),
    })
    if (res.ok) {
      const data: MealPlanFood = await res.json()
      const mpf: MealPlanFood = { ...data, food_data: food }
      emit('food-saved', mpf)

      if (!existingId) {
        draftRow.value = { _uid: makeUid(), _isDraft: true, id: null, food: null, amount_in_g: '' }
      }
    }
  } catch (e) {
    console.error('Failed to save row:', e)
  }
}

function onDeleteRow(row: DisplayRow) {
  if (row._isDraft) return
  emit('request-delete', row as MealPlanFood)
}

function onActivateSearch(payload: ActivateSearchPayload) {
  emit('activate-search', payload)
}
</script>
