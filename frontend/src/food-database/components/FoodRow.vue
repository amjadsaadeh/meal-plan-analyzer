<template>
  <tr class="food-row" @click="navigate">
    <td class="col-name">
      <span v-html="highlightMatch(food.name, searchQuery)"></span>
      <span v-if="food.matched_alias" class="alias-badge">
        {{ i18n.aliasBadge || 'alias' }}:
        <span v-html="highlightMatch(food.matched_alias, searchQuery)"></span>
      </span>
    </td>
    <td class="col-code">{{ food.bls_code }}</td>
    <td class="col-kcal">{{ formatKcal(food.energy_in_kcal_per_100g) }}</td>
    <td class="col-source">
      <span
        class="source-badge"
        :class="food.data_source === 'custom' ? 'source-custom' : 'source-bls'"
      >
        {{ food.data_source === 'custom' ? i18n.customBadge : i18n.blsBadge }}
      </span>
    </td>
  </tr>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import type { Food, I18n } from '../../types/index'

const props = withDefaults(defineProps<{
  food: Food
  searchQuery?: string
}>(), {
  searchQuery: '',
})

const i18n = inject<I18n>('i18n')!
const foodEditorBaseUrl = inject<string>('foodEditorBaseUrl')!

function navigate() {
  window.location.href = foodEditorBaseUrl + props.food.id + '/'
}

function formatKcal(val: number | null | undefined): string {
  if (val == null) return '—'
  return Number(val).toFixed(1)
}

function highlightMatch(text: string, query: string): string {
  if (!query) return text
  const semanticKeywords = ['low', 'high', 'energy', 'cal', 'kcal', 'kj']
  const tokens = query.toLowerCase().split(/\s+/)
    .filter(t => t.length >= 2 && !semanticKeywords.includes(t))
  if (tokens.length === 0) return text
  const pattern = tokens.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')
  return text.replace(regex, '<strong>$1</strong>')
}
</script>
