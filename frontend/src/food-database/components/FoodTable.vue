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
      <tr v-if="foods.length === 0 && !loading">
        <td colspan="4" class="empty-row">{{ i18n.noData }}</td>
      </tr>
      <FoodRow
        v-for="food in foods"
        :key="food.id"
        :food="food"
        :search-query="searchQuery"
      />
    </tbody>
  </table>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import FoodRow from './FoodRow.vue'
import type { Food, I18n } from '../../types/index'

withDefaults(defineProps<{
  foods?: Food[]
  loading?: boolean
  searchQuery?: string
}>(), {
  foods: () => [],
  loading: false,
  searchQuery: '',
})

const i18n = inject<I18n>('i18n')!
</script>
