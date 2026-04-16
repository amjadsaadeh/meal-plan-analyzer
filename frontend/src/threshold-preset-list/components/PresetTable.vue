<template>
  <table class="preset-table">
    <thead>
      <tr>
        <th class="col-name">{{ i18n.colName }}</th>
        <th
          v-for="key in DEFAULT_KEYS"
          :key="key"
          class="col-nutrient preset-nutrient-cell"
        >
          {{ labelFor(key) }}
        </th>
        <th class="col-actions"></th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="presets.length === 0 && !loading">
        <td :colspan="DEFAULT_KEYS.length + 2" class="empty-row">
          {{ i18n.noData }}
        </td>
      </tr>
      <PresetRow
        v-for="preset in presets"
        :key="preset.id"
        :preset="preset"
        :search-query="searchQuery"
      />
    </tbody>
  </table>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import PresetRow from './PresetRow.vue'
import type { ThresholdPreset, Nutrient, I18n } from '../../types/index'

withDefaults(defineProps<{
  presets?: ThresholdPreset[]
  loading?: boolean
  searchQuery?: string
}>(), {
  presets: () => [],
  loading: false,
  searchQuery: '',
})

const i18n = inject<I18n>('i18n')!
const nutrients = inject<Nutrient[]>('nutrients')!

const DEFAULT_KEYS = ['energy_in_kcal', 'water_in_g', 'carbohydrate_in_g', 'fat_in_g', 'protein_in_g']

function labelFor(key: string): string {
  const n = nutrients.find((x) => x.key === key)
  return n ? `${n.label} (${n.unit})` : key
}
</script>
