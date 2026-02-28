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
            @input="onThresholdChange(nut.key, 'min', $event.target.value)"
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
            @input="onThresholdChange(nut.key, 'max', $event.target.value)"
          >
        </div>
      </div>
    </div>
    <button class="btn-secondary" @click="$emit('open-save-preset')">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
        <polyline points="17 21 17 13 7 13 7 21"></polyline>
        <polyline points="7 3 7 8 15 8"></polyline>
      </svg>
      {{ i18n.saveAsTemplate }}
    </button>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'

const i18n = inject('i18n')

const props = defineProps({
  day: { type: Object, required: true },
  nutrients: { type: Array, default: () => [] },
  visibleNutrients: { type: Array, default: () => [] },
  thresholds: { type: Object, default: () => ({}) },
  allFoods: { type: Array, default: () => [] },
})

const emit = defineEmits(['open-save-preset', 'update-threshold'])

function dayTotal(nutKey) {
  const nut = props.nutrients.find(n => n.key === nutKey)
  if (!nut) return 0
  return props.allFoods.reduce((sum, f) => {
    if (!f.food_data) return sum
    return sum + (f.food_data[nut.food_key] || 0) * (f.amount_in_g || 0) / 100
  }, 0)
}

function thresholdVal(nutKey, type) {
  const t = props.thresholds?.[nutKey]
  if (!t) return ''
  const v = t[type]
  return v === null || v === undefined ? '' : v
}

function thresholdClass(nutKey) {
  const val = dayTotal(nutKey)
  const t = props.thresholds?.[nutKey] || {}
  const min = t.min !== null && t.min !== undefined ? parseFloat(t.min) : null
  const max = t.max !== null && t.max !== undefined ? parseFloat(t.max) : null
  if (min !== null && val < min) return 'status-under'
  if (max !== null && val > max) return 'status-over'
  return ''
}

function fmt(val, precision) {
  return (val || 0).toFixed(precision ?? 1)
}

function onThresholdChange(nutKey, type, value) {
  emit('update-threshold', { key: nutKey, type, value })
}
</script>
