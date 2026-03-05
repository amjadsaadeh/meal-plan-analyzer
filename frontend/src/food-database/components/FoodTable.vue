<template>
  <table class="food-table">
    <thead>
      <tr>
        <th class="col-name">{{ i18n.colName }}</th>
        <th class="col-code">{{ i18n.colCode }}</th>
        <th class="col-kcal">{{ i18n.colKcal }}</th>
        <th class="col-source">{{ i18n.colSource }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="loading">
        <td colspan="4" class="empty-row">
          <span class="loading-spinner"></span>
        </td>
      </tr>
      <tr v-else-if="foods.length === 0">
        <td colspan="4" class="empty-row">{{ i18n.noData }}</td>
      </tr>
      <FoodRow v-else v-for="food in foods" :key="food.id" :food="food" />
    </tbody>
  </table>
</template>

<script setup>
import { inject } from 'vue'
import FoodRow from './FoodRow.vue'

defineProps({
  foods: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const i18n = inject('i18n')
</script>
