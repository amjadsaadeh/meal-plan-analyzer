<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import MealPlanRow from './MealPlanRow.vue'
import type { MealPlan } from '../../api/types'

const { t } = useI18n()

defineProps<{ plans: MealPlan[] }>()

const emit = defineEmits<{
  navigate: [id: number]
  delete: [id: number]
}>()
</script>

<template>
  <table class="meal-plan-table">
    <thead>
      <tr>
        <th>{{ t('columnName') }}</th>
        <th>{{ t('columnDays') }}</th>
        <th>{{ t('columnCreated') }}</th>
        <th>{{ t('columnLastChanged') }}</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <MealPlanRow
        v-for="plan in plans"
        :key="plan.id"
        :plan="plan"
        @navigate="emit('navigate', $event)"
        @delete="emit('delete', $event)"
      />
      <tr v-if="plans.length === 0">
        <td colspan="5" class="no-data">{{ t('noMealPlansFound') }}</td>
      </tr>
    </tbody>
  </table>
</template>
