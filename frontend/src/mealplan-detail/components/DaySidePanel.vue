<template>
  <div class="day-summary">
    <h3 class="summary-title">{{ day.name }} - {{ i18n.daySummaryOverview }}</h3>
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
            @input="onThresholdChange(nut.key, 'min', ($event.target as HTMLInputElement).value)"
          >
          <span
            class="summary-val"
            :class="thresholdClass(nut.key)"
          >
            {{ fmt(dayTotal(nut.key), nut.precision) }}
          </span>
          <input
            type="number"
            class="threshold-input threshold-max"
            :data-nut="nut.key"
            :placeholder="i18n.max"
            :value="thresholdVal(nut.key, 'max')"
            @input="onThresholdChange(nut.key, 'max', ($event.target as HTMLInputElement).value)"
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
import type { I18n, Nutrient, MealPlanDay, MealPlanFood, ThresholdMap } from '../../types/index'

const i18n = inject<I18n>('i18n')!

const props = withDefaults(defineProps<{
  day: MealPlanDay
  nutrients?: Nutrient[]
  visibleNutrients?: string[]
  thresholds?: ThresholdMap
  allFoods?: MealPlanFood[]
}>(), {
  nutrients: () => [],
  visibleNutrients: () => [],
  thresholds: () => ({}),
  allFoods: () => [],
})

const emit = defineEmits<{
  'open-save-preset': []
  'update-threshold': [payload: { key: string; type: string; value: string }]
}>()

function dayTotal(nutKey: string): number {
  const nut = props.nutrients.find(n => n.key === nutKey)
  if (!nut) return 0
  return props.allFoods.reduce((sum, f) => {
    if (!f.food_data) return sum
    return sum + ((f.food_data[nut.food_key] as number) || 0) * (f.amount_in_g || 0) / 100
  }, 0)
}

function thresholdVal(nutKey: string, type: string): number | string {
  const t = props.thresholds?.[nutKey]
  if (!t) return ''
  const v = t[type as keyof typeof t]
  return v === null || v === undefined ? '' : v
}

function thresholdClass(nutKey: string): string {
  const val = dayTotal(nutKey)
  const t = props.thresholds?.[nutKey] || { min: null, max: null }
  const min = t.min !== null && t.min !== undefined ? parseFloat(String(t.min)) : null
  const max = t.max !== null && t.max !== undefined ? parseFloat(String(t.max)) : null
  if (min !== null && val < min * 0.95) return 'status-under'
  if (min !== null && val < min)        return 'status-warn'
  if (max !== null && val > max * 1.05) return 'status-over'
  if (max !== null && val > max)        return 'status-warn'
  return ''
}

function fmt(val: number, precision: number): string {
  return (val || 0).toFixed(precision ?? 1)
}

function onThresholdChange(nutKey: string, type: string, value: string) {
  emit('update-threshold', { key: nutKey, type, value })
}
</script>
