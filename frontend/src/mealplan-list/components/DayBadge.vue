<template>
  <a
    :href="`/meal-plan/${planId}/#day-${day.id}`"
    class="energy-badge"
    style="text-decoration: none;"
    @click.stop
  >
    {{ day.name }}
  </a>
</template>

<script setup lang="ts">
import type { MealPlanDay } from '../../types/index'

defineProps<{
  planId: number
  day: MealPlanDay
}>()
</script>
