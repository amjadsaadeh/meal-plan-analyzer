<template>
  <tr class="food-row" @click="navigate">
    <td class="col-name">
      <span v-html="highlightMatch(food.name, searchQuery)"></span>
      <span v-if="food.matched_alias" class="alias-badge" v-html="highlightMatch(food.matched_alias, searchQuery)"></span>
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

<script setup>
import { inject } from 'vue'

const props = defineProps({
  food: { type: Object, required: true },
  searchQuery: { type: String, default: '' },
})

const i18n = inject('i18n')
const foodEditorBaseUrl = inject('foodEditorBaseUrl')

function navigate() {
  window.location.href = foodEditorBaseUrl + props.food.id + '/'
}

function formatKcal(val) {
  if (val == null) return '—'
  return Number(val).toFixed(1)
}

function highlightMatch(text, query) {
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
