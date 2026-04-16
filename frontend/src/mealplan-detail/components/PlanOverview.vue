<template>
  <div class="meal-summary">
    <h3 class="summary-title">{{ i18n.planOverview }}</h3>
    <div class="summary-grid">
      <div
        v-for="nut in nutrients"
        :key="nut.key"
        class="summary-item"
        :class="['col-' + nut.key, { 'hidden-col': !visibleNutrients.includes(nut.key) && nut.key !== 'energy_in_kcal' }]"
      >
        <span class="summary-label">{{ nut.label }}</span>
        <div class="summary-values-wrapper">
          <input
            type="number"
            class="threshold-input threshold-min"
            :data-nut="nut.key"
            :placeholder="i18n.min"
            :value="thresholdVal(nut.key, 'min')"
            @input="emit('update-threshold', nut.key, 'min', ($event.target as HTMLInputElement).value)"
          >
          <span
            class="summary-val"
            :class="thresholdClass(nut.key)"
          >
            {{ fmt(planAvg(nut.key), nut.precision) }}
          </span>
          <input
            type="number"
            class="threshold-input threshold-max"
            :data-nut="nut.key"
            :placeholder="i18n.max"
            :value="thresholdVal(nut.key, 'max')"
            @input="emit('update-threshold', nut.key, 'max', ($event.target as HTMLInputElement).value)"
          >
        </div>
      </div>
    </div>
    <button class="btn-secondary" @click="emit('open-save-preset')">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
        <polyline points="17 21 17 13 7 13 7 21"></polyline>
        <polyline points="7 3 7 8 15 8"></polyline>
      </svg>
      {{ i18n.saveAsTemplate }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import type { I18n, Nutrient, MealPlanDay, ThresholdMap } from '../../types/index'

const i18n = inject<I18n>('i18n')!

const props = withDefaults(defineProps<{
  days?: MealPlanDay[]
  nutrients?: Nutrient[]
  visibleNutrients?: string[]
  thresholds?: ThresholdMap
}>(), {
  days: () => [],
  nutrients: () => [],
  visibleNutrients: () => [],
  thresholds: () => ({}),
})

const emit = defineEmits<{
  'open-save-preset': []
  'update-threshold': [key: string, type: string, value: string]
}>()

function dayTotal(day: MealPlanDay, nutKey: string): number {
  const nut = props.nutrients.find(n => n.key === nutKey)
  if (!nut) return 0
  return (day.foods || []).reduce((sum, f) => {
    if (!f.food_data) return sum
    return sum + ((f.food_data[nut.food_key] as number) || 0) * (f.amount_in_g || 0) / 100
  }, 0)
}

function planAvg(nutKey: string): number {
  const count = props.days.length
  if (count === 0) return 0
  const total = props.days.reduce((sum, d) => sum + dayTotal(d, nutKey), 0)
  return total / count
}

function thresholdVal(nutKey: string, type: string): number | string {
  const t = props.thresholds?.[nutKey]
  if (!t) return ''
  const v = t[type as keyof typeof t]
  return v === null || v === undefined ? '' : v
}

function thresholdClass(nutKey: string): string {
  const val = planAvg(nutKey)
  const t = props.thresholds?.[nutKey] || { min: null, max: null }
  const min = t.min !== null && t.min !== undefined ? parseFloat(String(t.min)) : null
  const max = t.max !== null && t.max !== undefined ? parseFloat(String(t.max)) : null
  if (min !== null && val < min) return 'status-under'
  if (max !== null && val > max) return 'status-over'
  return ''
}

function fmt(val: number, precision: number): string {
  return (val || 0).toFixed(precision ?? 1)
}
</script>
