<template>
  <table>
    <thead>
      <tr>
        <th style="width: 40px;"></th>
        <th>{{ colName }}</th>
        <th>{{ colDays }}</th>
        <th>{{ colCreated }}</th>
        <th>{{ colChanged }}</th>
        <th class="actions-cell"></th>
      </tr>
    </thead>
    <tbody>
      <template v-if="loading">
        <tr>
          <td colspan="6" class="no-data">...</td>
        </tr>
      </template>
      <template v-else-if="plans.length === 0">
        <tr>
          <td colspan="6" class="no-data">{{ noDataText }}</td>
        </tr>
      </template>
      <template v-else>
        <MealPlanRow
          v-for="plan in plans"
          :key="plan.id"
          :plan="plan"
          :search-query="searchQuery"
          :no-days-text="noDaysText"
        />
      </template>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import MealPlanRow from './MealPlanRow.vue'
import type { MealPlan } from '../../types/index'

withDefaults(defineProps<{
  plans?: MealPlan[]
  searchQuery?: string
  loading?: boolean
  colName?: string
  colDays?: string
  colCreated?: string
  colChanged?: string
  noDataText?: string
  noDaysText?: string
}>(), {
  plans: () => [],
  searchQuery: '',
  loading: false,
  colName: 'Name',
  colDays: 'Days',
  colCreated: 'Created',
  colChanged: 'Last Changed',
  noDataText: 'No meal plans found.',
  noDaysText: 'No days',
})
</script>
