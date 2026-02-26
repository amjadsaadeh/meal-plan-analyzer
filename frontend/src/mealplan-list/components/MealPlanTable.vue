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

<script setup>
import MealPlanRow from './MealPlanRow.vue'

defineProps({
  plans: { type: Array, default: () => [] },
  searchQuery: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  colName: { type: String, default: 'Name' },
  colDays: { type: String, default: 'Days' },
  colCreated: { type: String, default: 'Created' },
  colChanged: { type: String, default: 'Last Changed' },
  noDataText: { type: String, default: 'No meal plans found.' },
  noDaysText: { type: String, default: 'No days' },
})
</script>
