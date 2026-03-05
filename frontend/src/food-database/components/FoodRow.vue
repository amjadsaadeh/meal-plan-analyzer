<template>
  <tr class="food-row" @click="navigate">
    <td class="col-name">
      {{ food.name }}
      <span v-if="food.matched_alias" class="alias-badge">{{ food.matched_alias }}</span>
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
</script>
